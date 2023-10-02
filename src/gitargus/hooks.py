import boto3
import uuid
import os
import json
from gitargus.core import Config

def pre_push():
    config = Config(os.path.expanduser('~') + "/.gitargus/config.yml")

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
