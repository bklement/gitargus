# GitArgus

Python utility to synchronize state of git workspaces for developers who use multiple machines. Uses AWS free tier DynamoDB to store the state. Can automatically pull changes if fast-forwarding is possible. Currently version only supports Unix systems.

## Installation

```
pip install gitargus
```

## AWS Infrastructure setup

You can create a free [AWS](https://aws.amazon.com) account and use the always-free allowance to run GitArgus. Consult AWS documentation on how to perform the required steps.

Create a DynamoDB table with a String partition key named 'hostname'. 1 read and write capacity should be enough, but turning on capacity auto scaling is recommended.

Install aws-cli to each machine you will run GitArgus on. Log in with a user and save it's credentails who has permission to write to the DynamoDB table. GitArgus will pick up these credentials.

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
timezone: Europe/Budapest
```

- **hostname** - the name of the machine, will be used as key in DynamoDB
- **root** - the directory where the repositories are
- **repositories** - list of the repositories to handle, can handle multiple directory levels
- **aws.dynamodb.table** - the name of the DynamoDB table
- **timezone** - timezone of the timestamps, useful in case of remote machines in different timezones

## Useage

You can start the process with the following command:

```
python -m gitargus
```

Either you can run manually or set up a cron job.

## Logs

The log file is located at `~/.gitargus/gitargus.log`.

## User Interface

The server.py file can be used for a stop-gap method to check the contents of the DynamoDB table. First install uvicorn, then run it with `uvicorn server:app`. Then use the url `http://127.0.0.1:8000/{hostname}` to access the json response. This is a temporary solution and will be removed before realese.

A MacOS/iPadOS/iOS application is in the very early stages of development.
