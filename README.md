# GitArgus

Python utility to synchronize state of git workspaces for developers who use multiple machines. Uses AWS free tier services (DynamoDB, SNS, SQS) to store the state and send events. Can automatically pull changes if fast-forwarding is possible. Currently version only supports Unix systems.

## Installation

The alpha version is currently hosted at [TestPyPi](https://test.pypi.org/project/gitargus/). You have to install dependencies first from PyPi:

```
pip install yaml pytz json pathspec boto3
```

Then install GitArgus:

```
pip install -i https://test.pypi.org/simple/ gitargus
```

## AWS Infrastructure setup

You can create a free [AWS](https://aws.amazon.com) account and use the always-free allowance to run GitArgus. Consult AWS documentation on how to perform the required steps.

Create a DynamoDB table with a String partition key named 'hostname'. 1 read and write capacity should be enough, but turning on capacity auto scaling is recommended.

Create an FIFO topic in SNS. These will be used to distribute git push events, so other machines can update their status and pull the changes if fast-forwarding is possible.

Create FIFO queues for each machine you will be using GitArgus. Delivery delay should be at least 10 seconds, because the notifications are sent from a pre-push git hook. Message retention shouldn't be more than a couple minutes, since the daemon will purge the queue at startup, and do a full update instead of processing the events. Subsribe the queues to the SNS topic created in the previous steps.

Install aws-cli to each machine you will run GitArgus on. Log in with a user and save it's credentails who has permissions to write to the DynamoDB table, publish to the SNS topic, and read from the SQS queues. GitArgus will pick up these credentials.

## Configuration

Create the '.gitargus' directory in your home folder, and create the configuration file 'config.yml':

```
hostname: machine
root: /home/user/Workspace
repositories:
    - repo1
    - repo2
    - project1/repo1
    - project2/repo1
    - project2/repo2
aws:
    dynamodb:
        table: git
    sqs:
        queue: machine.fifo
    sns:
        topic:
            arn: arn:aws:sns:{region}:{userId}:{topicName}
timezone: Europe/Budapest
python: 
    bin: /usr/bin/python3.11
```

- **hostname** - the name of the machine, will be used as key in DynamoDB
- **roor** - the directory where the repositories are
- **repositories** - list of the repositories to handle, can handle multiple directory levels
- **aws.dynamodb.table** - the name of the DynamoDB table
- **aws.sqq.queue** - the name of the SQS queue crated for this machine
- **aws.sns.topic.arn** - the SNS topic arn, you can access it in AWS console
- **timezone** - timezone of the timestamps, useful in case of remote machines in different timezones
- **python.bin** - location of the python binary with GitArgus installed, used to run hooks

## Hooks

From 1.0.0-alpha7 onwards, the daemon checks the existence of hooks on startup in the configured repositories. After updating the repository list in the configuration, a restart is necessary.

## Useage

You can start the daemon with the following command:

```
python -m gitargus
```

## Ubuntu Service

Create a service file at '/etc/systemd/system/gitargus@.service' with the following content:

```
[Unit]
Description=GitArgus daemon for %i

[Service]
User=%i
ExecStart=/usr/bin/python -m gitargus
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable the service for the specific user:

```
systemctl daemon-reload
systemctl enable --now gitargus@user
```

## Logs

The log file is located at `~/.gitargus/gitargus.log`.

## User Interface

The server.py file can be used for a stop-gap method to check the contents of the DynamoDB table. First install uvicorn, then run it with `uvicorn server:app`. Then use the url `http://127.0.0.1:8000/{hostname}` to access the json response. This is a temporary solution and will be removed before realese.

A MacOS/iPadOS/iOS application is in the very early stages of development.

## Known Issues

- Unnecessarily firing multiple events after a git pull
- If deamon restarts before the SQS queue purge finishes it fails with an error
