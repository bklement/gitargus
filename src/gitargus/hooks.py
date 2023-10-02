import boto3
import uuid
import os
import json
from gitargus.core import Config, CLI

config = Config(os.path.expanduser('~') + "/.gitargus/config.yml")
cli = CLI("/")

def install():
    for repository in config.repositories():
        filename = config.root() + "/" + repository + "/.git/hooks/pre-push"
        if not os.path.exists(filename):
            with open(filename, "w") as file:
                file.write("#!" + config.getProperty("python.bin") + "\n")
                file.write("from gitargus import hooks\n\n")
                file.write("hooks.pre_push()\n")
            cli.run(["chmod", "+x", filename])

def pre_push():
    
    message = {
        "source": config.hostname(),
        "type": "RepositoryFullUpdateJob",
        "repository": os.getcwd().replace(config.root() + "/", "")
    }

    sns = boto3.client('sns')
    sns.publish(
        TopicArn=config.getProperty("aws.sns.topic.arn"),
        Message=json.dumps(message),
        MessageGroupId="git",
        MessageDeduplicationId=uuid.uuid4().hex
    )

    exit(0)
