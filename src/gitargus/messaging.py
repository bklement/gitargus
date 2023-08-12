from abc import ABC, abstractmethod
import boto3
import time
import json
from jobs import RepositoryFullUpdateJob
from multiprocessing import Queue
from core import Workspace, logging

class Listener(ABC):

    def __init__(self, queueName: str):
        self.__queueName = queueName

    @abstractmethod
    def listen(self):
        pass

class SQSListener(Listener):

    def __init__(self, hostname: str, workspace: Workspace, queue: Queue, queueName: str):
        self.__hostname = hostname
        self.__workspace = workspace
        self.__queue = queue
        self.__queueUrl = boto3.client("sqs").get_queue_url(QueueName=queueName)['QueueUrl']
        logging.info("Purging SQS queue {}, sleeping for 60 seconds to complete.".format(queueName))
        boto3.client("sqs").purge_queue(QueueUrl=self.__queueUrl)
        time.sleep(60)
        logging.info("Purged SQS queue {}.".format(queueName))

    def listen(self):
        sqs = boto3.client("sqs")
        while True:
            logging.debug("Polling SQS.")
            response = sqs.receive_message(
                QueueUrl=self.__queueUrl,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=5
            )
            if ("Messages" in response):
                logging.debug("Message recieved from SQS.")
                message = response["Messages"][0]
                receiptHandle = message["ReceiptHandle"]
                body = json.loads(message["Body"])

                logging.info("Message recieved from SQS: {}".format(body["Message"]))
                jobDescription = json.loads(body["Message"])               

                if jobDescription["source"] != self.__hostname:
                    logging.info("Processing message from {}.".format(jobDescription["source"]))
                    if jobDescription["type"] == "RepositoryFullUpdateJob":
                        job = RepositoryFullUpdateJob(self.__workspace.getRepository(jobDescription["repository"]))
                        self.__queue.put(job, block=False, timeout=2)
                    else:
                        logging.warn("Unrecognized job type {}.".format(jobDescription["type"]))
                else:
                    logging.info("Message originated from {}, skipping.".format(jobDescription["source"]))

                logging.debug("Deleting message from SQS.")
                sqs.delete_message(
                    QueueUrl=self.__queueUrl,
                    ReceiptHandle=receiptHandle
                )
                logging.debug("Message deleted from SQS.")
            else:
                logging.debug("No new message recieved from SQS.")
                time.sleep(40)