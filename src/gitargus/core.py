from datetime import datetime
import pytz
import yaml
import os
import logging
import boto3
import urllib
from subprocess import run, CalledProcessError


logging.basicConfig(filename=os.path.expanduser('~') + "/.gitargus/gitargus.log",
                    encoding="utf-8",
                    level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def log(s: str):
    print(s)
    logging.info(s)


class Config():

    def __init__(self):
        log("Checking internet connection...")
        try:
            urllib.request.urlopen("http://github.com")
        except Exception:
            log("No internet connection, exiting.")
            exit(-1)
        log("We are online! Reading config file.")
        with open(os.path.expanduser('~') + "/.gitargus/config.yml", "r") as configFile:
            self.__config = yaml.safe_load(configFile)

    def root(self):
        return self.__config["root"]

    def repositories(self):
        return self.__config["repositories"]

    def timezone(self):
        return self.__config["timezone"]

    def hostname(self):
        return self.__config["hostname"]

    def table(self):
        return self.__config["aws"]["dynamodb"]["table"]


class CLI():

    def __init__(self, folder: str):
        self.__folder = folder

    def run(self, params):
        try:
            os.chdir(self.__folder)
        except FileNotFoundError:
            log("Tried to change to folder '{}' but it does not exist.".format(self.__folder))
            return None
        try:
            p = run(params, check=True, capture_output=True, text=True)
            return p.stdout
        except CalledProcessError as e:
            log("Error running subprocess '{}' in '{}':\n{}".format(" ".join(params), os.getcwd(), e))
        except FileNotFoundError:
            log("Tried to run command '{}', but it does not exist.".format(params[0]))


class Dynamodb():

    def __init__(self, hostname: str, table: str):
        self.__hostname = hostname
        self.__table = table
        log("Dynamodb created with hostname {} and table {}.".format(hostname, table))

    def save(self, results: dict):
        log("Saving to dynamodb.")
        # log("Payload to dynamodb: {}".format(dict))
        item = {"hostname": self.__hostname}
        item.update(results)
        boto3.resource("dynamodb").Table(self.__table).put_item(TableName=self.__table, Item=item)


class Repository():

    def __init__(self, root: str, name: str, timezone: str):
        self.__folder = root + "/" + name
        self.__cli = CLI(self.__folder)
        self.__name = name
        self.__timezone = timezone

    def __timestamp(self):
        return datetime.now(pytz.timezone(self.__timezone)).strftime("%Y-%m-%d %H:%M:%S")

    def __pull(self):
        log("Pulling repository {} if fast-forwarding is possible.".format(self.__name))
        outcome = self.__cli.run(["git", "pull", "--ff-only"])
        if outcome == "fatal: Not possible to fast-forward, aborting.":
            log("Fast-forward failed.")
            return False
        elif outcome is None:
            return False
        else:
            log("Successfully fast-forwarded.")
            return True

    def __getState(self, header):
        if header.endswith("]"):
            if ("ahead" in header):
                if ("behind" in header):
                    return "DIVERGED"
                else:
                    return "AHEAD"
            else:
                return "BEHIND"
        else:
            return "UP_TO_DATE"

    def getStatus(self):
        log("Fetching repository {}".format(self.__name))
        self.__cli.run(["git", "fetch", "--all"])
        log("Reading repository status for {}".format(self.__name))
        stdout = self.__cli.run(["git", "status", "-sb"])
        if stdout is None:
            return {self.__name: {
                "timestamp": self.__timestamp(),
                "state": "FAILED_UPDATE"
            }}
        else:
            result = stdout.split("\n")
            result.remove("")
            header = result[0].replace("## ", "").replace("\n", "").split("...")
            local = header[0]
            remote = header[1].split(" ")[0]
            state = self.__getState(header[1])
            if (state == "BEHIND" or state == "DIVERGED"):
                if (self.__pull()):
                    return self.getStatus()
            changes = result[1:]
            if changes:
                clean = False
            else:
                clean = True
            return {self.__name: {
                "timestamp": self.__timestamp(),
                "local": local,
                "remote": remote,
                "state": state,
                "clean": clean,
                "changes": changes
            }}


class Workspace():

    def __init__(self, root: str, repositoryNames: list, timezone: str):
        self.__repositories = {}
        for name in repositoryNames:
            if os.path.exists(root + "/" + name):
                self.__repositories.update({
                    name: Repository(root, name, timezone)
                })
            else:
                log("Repository {} does not exists on the filesystem in workspace {}.".format(name, root))

    def readRepositoryStatuses(self):
        results = {}
        for _, repository in self.__repositories.items():
            results.update(repository.getStatus())
        return results
