from abc import ABC, abstractmethod
from gitargus.core import logging
import boto3


class Database(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def save(self, results: dict):
        pass

    @abstractmethod
    def update(self, repositoryName: str, status: dict):
        pass


class Dynamodb(Database):

    def __init__(self, hostname: str, table: str):
        self.__hostname = hostname
        self.__table = table
        logging.debug(
            "Dynamodb created with hostname {} and table {}."
            .format(hostname, table)
        )

    def save(self, results: dict):
        logging.debug(
            "Saving to dynamodb: {}"
            .format(dict)
        )
        item = {"hostname": self.__hostname}
        item.update(results)
        boto3.resource("dynamodb").Table(self.__table).put_item(TableName=self.__table, Item=item)

    def update(self, repositoryName: str, status: dict):
        boto3.resource("dynamodb").Table(self.__table).update_item(
            Key={"hostname": self.__hostname},
            UpdateExpression="set #r=:s",
            ExpressionAttributeValues={':s': status[repositoryName]},
            ExpressionAttributeNames={"#r": repositoryName}
        )

class Mukodj:

    def __init__(self):
        pass