from abc import ABC, abstractmethod
from core import logging
import boto3

class Database(ABC):

    def __init__(self, hostname: str):
        self.__hostname = hostname

    @abstractmethod
    def save(self, results: dict):
        pass

    @abstractmethod
    def update(self, repositoryName: str, status: dict):
        pass

class Dynamodb(Database):

    def __init__(self, hostname: str, table: str):
        super().__init__(hostname)
        self.__table = table
        logging.debug("Dynamodb created with hostname {} and table {}.".format(hostname, table))


    def save(self, results : dict):
        logging.debug("Saving to dynamodb: {}".format(dict))
        item = {"hostname": self._Database__hostname}
        item.update(results)
        boto3.resource("dynamodb").Table(self.__table).put_item(TableName=self.__table, Item=item)

    def update(self, repositoryName: str, status: dict):
        boto3.resource("dynamodb").Table(self.__table).update_item(
            Key={"hostname": self._Database__hostname},
            UpdateExpression="set #r=:s",
            ExpressionAttributeValues={':s': status[repositoryName]},
            ExpressionAttributeNames={"#r": repositoryName}
        )