import json
import os
import re
from datetime import datetime
from urllib.parse import parse_qs

import pytz
from dateutil import parser
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Slack client requires auth token from app config.
# This is set as an environment variable in the SAM template.
token = os.environ.get("SlackAppToken")
client = WebClient(token=token)


# Currently supports four major timezones for continental US.
# Alter this list according to your own team's needs.
US_TIMEZONES = {
    'Eastern': 'America/New_York',
    'Central': 'America/Chicago',
    'Mountain': 'America/Denver',
    'Pacific': 'America/Los_Angeles'
}

# Attempts to match the following time formats:
# Hour and minute: 6:30, 06:30, 12:30
# Hour and meridian: 2pm, 10am, 3 p.m., 8 AM
# Hour, minute, and meridian: 5:20 p.m., 08:00 AM, 12:00pm
TIME_REGEX = (
    r'(0?[1-9]|1[0-2]):([0-5][0-9]) ?'
    r'([ap]\.?m\.?)?|(0?[1-9]|1[0-2]) ?([ap]\.?m\.?)'
)


def format_time(dt):
    """
    Remove leading zeros and lowercase the meridian.
    For example, 06:00 PM will be converted to 6:00 pm.
    """
    ftime = dt.strftime('%I:%M %p')
    ftime = re.sub(r'^0(\d):', r'\1:', ftime)
    ftime = ftime.lower()
    return ftime


def extract_data(body, body_json):
    """
    Get the required data from Slack message body.
    """
    if body_json.get('event'):
        # The data has been sent via the Events API.
        slack_event = body_json['event']
        user_id = slack_event['user']
        channel_id = slack_event['channel']
        text = slack_event['text'].replace(f'<@{user_id}>', '')
        thread_ts = slack_event.get('thread_ts')
    else:
        # The data has been sent via a slash command.
        qs = parse_qs(body)
        user_id = qs.get('user_id')[0]
        channel_id = qs.get('channel_id')[0]
        text = qs.get('text')[0]
        thread_ts = None

    print('user_id: ', user_id)
    print('channel_id: ', channel_id)
    print('text: ', text)
    print('thread_ts: ', thread_ts)

    return user_id, channel_id, text, thread_ts


def get_msg_time(match):
    """
    Parse the matched time.
    """
    if match.group(4) and match.group(5):
        # Matches hour + meridian, e.g. 11am
        print(f"Matched time: {match.group(4)}{match.group(5)}")
        return parser.parse(f"{match.group(4)}:00 {match.group(5)}").time()
    elif match.group(1) and match.group(2):
        if match.group(3):
            # Matches hour + minutes + meridian, e.g. 11:30 am
            print(f"Matched time: {match.group(1)}:{match.group(2)}{match.group(3)}")
            return parser.parse(
                f"{match.group(1)}:{match.group(2)} {match.group(3)}"
            ).time()
        else:
            # Matches hour + minutes, 11:30
            print(f"Matched time: {match.group(1)}:{match.group(2)}")
            # Make a best-guess about the meridian based on normal business hours
            m = 'am' if int(match.group(2)) in (7, 8, 9, 10, 11) else 'pm'
            return parser.parse(f"{match.group(1)}:{match.group(2)} {m}").time()


def get_full_response(user_id, text):
    """
    Using the user's timezone as a reference point, construct
    a response that converts all times in their message to
    other timezones.
    """
    try:
        # Look up the user's profile to get their timezone info
        response = client.users_info(user=user_id, include_locale=True)
        print('slack response: ', response)
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")

    tz = response['user']['tz']
    tz_label = response['user']['tz_label']
    user_tz = pytz.timezone(tz)

    print('tz: ', tz)
    print('tz_label: ', tz_label)
    print('user_tz: ', user_tz)

    responses = []

    for match in re.finditer(TIME_REGEX, text, re.IGNORECASE):
        print(
            f'match 0: {match.group(0)}, match 1: {match.group(1)}, '
            f'match 2: {match.group(2)}, match 3: {match.group(3)}, '
            f'match 4: {match.group(4)}, match 5: {match.group(5)} '
        )

        msg_time = get_msg_time(match)
        user_datetime = datetime.now(user_tz).replace(
            hour=msg_time.hour, minute=msg_time.minute
        )

        print('user_datetime: ', user_datetime)

        other_times = []
        user_tz_name = next(k for k, v in US_TIMEZONES.items() if v == tz)

        for tz_name, tz_str in US_TIMEZONES.items():
            timezone = pytz.timezone(tz_str)
            datetime_tz = user_datetime.astimezone(timezone)
            if tz_str != tz:
                other_times.append(f"{format_time(datetime_tz)} {tz_name}")

        responses.append(
            f":magic_wand: _{format_time(user_datetime)} "
            f"{user_tz_name} is {', '.join(other_times)}_"
        )

    return '\n'.join(responses)



def get_return_value(body_json, channel_id, full_response, thread_ts):
    """
    If we're processing a bot event, post the response via the API
    using the chat.postMessage method.  If we're returning a response
    to a slash command, return the full response in channel.
    """
    if body_json.get('event'):
        # Post a response in the channel via the API.
        try:
            response = client.chat_postMessage(
                channel=channel_id, text=full_response, thread_ts=thread_ts
            )
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")

        return {
            "statusCode": 200,
            "body": "OK"
        }

    else:
        # Return the text of the response as an in-channel message.
        return {
            "statusCode": 200,
            "body": json.dumps({
                "response_type": "in_channel",
                "text": full_response
            }),
        }


def lambda_handler(event, context):

    print('event: ', event)

    body = event.get("body")

    try:
        body_json = json.loads(body)
    except:
        print('Could not load body as JSON')
        body_json = {}

    # If Slack sends a challenge, return it.
    challenge = body_json.get('challenge')
    if challenge:
        print('challenge', challenge)
        return {
            "statusCode": 200,
            "body": challenge,
        }

    user_id, channel_id, text, thread_ts = extract_data(body, body_json)

    full_response = get_full_response(user_id, text)

    return get_return_value(body_json, channel_id, full_response, thread_ts)
