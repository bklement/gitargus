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


def parse(header: str):
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


class Dynamodb():

    def __init__(self, hostname: str, table: str):
        self.__hostname = hostname
        self.__table = table
        log("Dynamodb created with hostname {} and table {}.".format(hostname, table))

    def save(self, results: dict):
        log("Saving to dynamodb.")
        item = {"hostname": self.__hostname}
        item.update(results)
        boto3.resource("dynamodb").Table(self.__table).put_item(TableName=self.__table, Item=item)


class Repository():

    def __init__(self, parent: str, name: str, origin: str):
        self.__parentFolder = parent
        self.__name = name
        self.__folder = parent + "/" + name
        self.__origin = origin

    def __run(self, params: list, folder: str = None, supressErrors: bool = False):
        try:
            if folder is None:
                os.chdir(self.__folder)
            else:
                os.chdir(folder)
        except FileNotFoundError:
            log("Tried to change to folder '{}' but it does not exist.".format(self.__folder))
            return None
        try:
            p = run(params, check=True, capture_output=True, text=True)
            return p.stdout
        except CalledProcessError as e:
            if not supressErrors:
                log("Error running subprocess '{}' in '{}':\n{}".format(" ".join(params), os.getcwd(), e))
        except FileNotFoundError:
            if not supressErrors:
                log("Tried to run command '{}', but it does not exist.".format(params[0]))

    def pull(self):
        log("Pulling repository {} if fast-forwarding is possible.".format(self.__name))
        outcome = self.__run(["git", "pull", "--ff-only"])
        if outcome == "fatal: Not possible to fast-forward, aborting.":
            log("Fast-forward failed.")
            return False
        elif outcome is None:
            return False
        else:
            log("Successfully fast-forwarded.")
            return True

    def getStatus(self, fetch: bool = True):
        if fetch:
            log("Fetching repository {}".format(self.__name))
            self.__run(["git", "fetch", "--all"])
        log("Reading repository status for {}".format(self.__name))
        stdout = self.__run(["git", "status", "-sb"])
        if stdout is None:
            return {self.__name: {
                "state": "FAILED_UPDATE"
            }}
        else:
            result = stdout.split("\n")
            result.remove("")
            header = result[0].replace("## ", "").replace("\n", "").split("...")
            local = header[0]
            if len(header) == 1:
                remote = None
                state = "LOCAL_ONLY"
            else:
                remote = header[1].split(" ")[0]
                state = parse(header[1])
                if (state == "BEHIND" or state == "DIVERGED"):
                    if (self.pull()):
                        return self.getStatus()
            changes = result[1:]
            if changes:
                clean = False
            else:
                clean = True
            return {self.__name: {
                "local": local,
                "remote": remote,
                "state": state,
                "clean": clean,
                "changes": changes
            }}

    def install(self):
        if os.path.exists(self.__parentFolder):
            log("Parent folder already exists: {}, skipping.".format(self.__parentFolder))
        else:
            try:
                p = run(["mkdir", "-p", self.__folder], check=True, capture_output=True, text=True)
                return p.stdout
            except CalledProcessError as e:
                log("Error creating folder {}:\n{}".format(self.__folder, e))
            except FileNotFoundError:
                log("Tried to run command '{}', but it does not exist.".format("mkdir"))
        if not os.path.exists(self.__folder) or self.__run(["git", "status"], self.__folder, True) is None:
            log("Pulling repository {}...".format(self.__name))
            self.__run(["git", "clone", self.__origin], self.__parentFolder)
            log("Success.")
        else:
            log("Tried to pull already present repository: {}, skipping.".format(self.__folder))


class Workspace():

    def __init__(self, root: str, repositories: dict, timezone: str):
        if os.path.exists(root):
            log("Found root directory {}".format(root))
        else:
            log("Root does not exists on the filesystem, exiting.")
            exit(-1)
        self.__timezone = pytz.timezone(timezone)
        self.__repositories = []
        self.__dict = {}
        self.__extractRepositories(root, repositories)

    def __extractRepositories(self, parent: str, dictionary: dict):
        for key in dictionary.keys():
            if isinstance(dictionary[key], dict):
                self.__extractRepositories(parent + "/" + key, dictionary[key])
            else:
                self.__repositories.append(Repository(parent, key, dictionary[key]))

    def readRepositoryStatuses(self, fetch: bool = True):
        statuses = {}
        for repository in self.__repositories:
            status = repository.getStatus(fetch)
            status[list(status.keys())[0]].update({"timestamp": datetime.now(self.__timezone).strftime("%Y-%m-%d %H:%M:%S")})
            statuses.update(status)
        return statuses

    def install(self):
        for repository in self.__repositories:
            repository.install()
