# 🪄 Timezone Wand 🪄

Timezone Wand is a serverless Slack app for timezone conversions.

It is intended for organizations that need to self-host their Slack apps (e.g. to comply with security policies).

If your organization does not need to self host, consider a solution like [Timezone Butler](https://slack.com/apps/AE9AXUV4G-timezone-butler), which is easier to set up.

Timezone Wand is built on the AWS Serverless Application Model (SAM) and contains everything you need to deploy the required serverless resources.  The only thing you'll need to supply is your Slack app's API token.


## Using the app

You can use Timezone Wand as either a slash command or a bot.

As a Slash command, enter `/tz` followed by a message that contains a time.  Timezone Wand will then post timezone conversions.  Note: Slash commands cannot be used within threads.

As a bot, mention `@Timezone Wand` followed by a message that contains a time.  Timezone Wand will then post timezone conversions.  Note: This will work in threads.


<img width="576" alt="timezone-wand-screenshot" src="https://user-images.githubusercontent.com/917943/235697083-87914ac5-5447-4ed2-bae6-4785ef77c593.png">


## Overview

When you deploy Timezone Wand, it creates an AWS Lamba function and an associated API Gateway.

Because the Lambda is serverless, you will only be billed when the function is actually invoked.

The function's handler is in `functions/app.py`.  That file contains all the core logic used to support Timezone Wand as either a slash command or a bot.


## Set up app

After deploying the serverless resources (see below), take note of the API Gateway endpoint URL.

Open the `slack-manifest.yaml` file and add that URL to the three places where `[insert URL of your API Gateway endpoint here]` is present.

[Create a new Slack application](https://api.slack.com/apps) using the manifest in `slack-manifest.yaml`.

Install the app to your workspace.

Finally, grab the authentication token from the OAuth section of the app configuration page and supply it
as an environment variable (will require a re-deploy).  You can either enter it into the `template.yaml`
file or supply it when you `sam deploy`.


## Deployment

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

You can find your API Gateway Endpoint URL in the output values displayed after deployment.
