from datetime import datetime
import pytz
import yaml
import logging
import os
from subprocess import run, CalledProcessError
from pathspec import PathSpec, GitWildMatchPattern

WORK_DIR = os.path.expanduser('~') + "/.gitargus/"
logging.basicConfig(filename=WORK_DIR + "gitargus.log",
                    encoding="utf-8",
                    level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


class Config():

    def __init__(self, configFileName: str):
        with open(configFileName, "r") as configFile:
            logging.debug("Opening config file.")
            self.__config = yaml.safe_load(configFile)
            logging.debug("Config file read.")

    def root(self):
        return self.getProperty("root")

    def repositories(self):
        return self.getProperty("repositories")

    def timezone(self):
        return self.getProperty("timezone")

    def hostname(self):
        return self.getProperty("hostname")

    def table(self):
        return self.getProperty("aws.dynamodb.table")

    def queue(self):
        return self.getProperty("aws.sqs.queue")

    def getProperty(self, name: str):
        logging.debug("Reading property {}.".format(name))
        keys = name.split(".")
        temp = self.__config
        for key in keys:
            temp = temp[key]
        return temp

    def hasProperty(self, name: str):
        return name in self.__config


class CLI():

    def __init__(self, folder: str):
        self.__folder = folder
        logging.debug("CLI initialized for {}.".format(folder))

    def run(self, params):
        try:
            os.chdir(self.__folder)
        except FileNotFoundError:
            logging.error(
                "Tried to change to folder '{}' but it does not exist."
                .format(self.__folder)
            )
            return None
        try:
            logging.debug(
                "Changed dir to {}. Running process {}."
                .format(self.__folder, params)
            )
            p = run(params, check=True, capture_output=True, text=True)
            return p.stdout
        except CalledProcessError as e:
            logging.error(
                "Error running subprocess '{}' in '{}':\n{}"
                .format(" ".join(params), os.getcwd(), e)
            )
        except FileNotFoundError:
            logging.error(
                "Tried to run command '{}', but it does not exist."
                .format(params[0])
            )


class GitIgnore():

    def __init__(self, folder: str):
        logging.debug("Reading .gitingore for {}.".format(folder))
        if os.path.exists(folder + "/.gitignore"):
            with open(folder + "/.gitignore", "r") as gitignore:
                logging.debug("Found .gitingore for {}.".format(folder))
                lines = gitignore.read().split("\n")
                while ("" in lines):
                    lines.remove("")
                lines.append(".git")
        else:
            logging.debug(
                ".gitingore not found for {}, initializing default patterns."
                .format(folder)
            )
            lines = [".git", "**/.DS_Store"]
        self.__pathspec = PathSpec.from_lines(GitWildMatchPattern, lines)
        logging.debug("GitIgnore initialized for {}.".format(folder))

    def isIgnored(self, path):
        return self.__pathspec.match_file(path)


class Repository():

    def __init__(self, root: str, name: str, timezone: str):
        self.__folder = root + "/" + name
        self.__cli = CLI(self.__folder)
        self.__gitIgnore = GitIgnore(self.__folder)
        self.__name = name
        self.__timezone = timezone
        logging.debug(
            "Creating repository {} in workspace {}."
            .format(name, root)
        )

    def __timestamp(self):
        return datetime.now(pytz.timezone(self.__timezone)).strftime("%Y-%m-%d %H:%M:%S")

    def __pull(self):
        logging.info(
            "Pulling repository {} if fast-forwarding is possible."
            .format(self.__name)
        )
        outcome = self.__cli.run(["git", "pull", "--ff-only"])
        if outcome == "fatal: Not possible to fast-forward, aborting.":
            logging.info("Fast-forward failed.")
            return False
        elif outcome is None:
            return False
        else:
            logging.info("Successfully fast-forwarded.")
            return True

    def __getState(self, header):
        logging.debug("Parsing state: {}.".format(header))
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
        stdout = self.__cli.run(["git", "status", "-sb"])
        if stdout is None:
            return {self.__name: {
                "timestamp": self.__timestamp(),
                "state": "FAILED_UPDATE"
            }}
        else:
            result = stdout.split("\n")
            logging.debug(
                "Git status read for {}: {}."
                .format(self.__name, result)
            )
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

    def fetch(self):
        logging.info("Fetching repository {}".format(self.__name))
        self.__cli.run(["git", "fetch", "--all"])

    def name(self):
        return self.__name

    def pathMatches(self, path: str):
        return path.startswith(self.__folder)

    def isIgnored(self, path):
        self.__gitIgnore.isIgnored(path)

    def getFolder(self):
        return self.__folder


class Workspace():

    def __init__(self, root: str, repositoryNames: list, timezone: str):
        self.__repositories = {}
        for name in repositoryNames:
            if os.path.exists(root + "/" + name):
                self.__repositories.update({
                    name: Repository(root, name, timezone)
                })
            else:
                logging.error(
                    "Repository {} does not exists on the filesystem in workspace {}."
                    .format(name, root)
                )

    def readRepositoryStatuses(self, fetch: bool):
        results = {}
        for _, repository in self.__repositories.items():
            if (fetch):
                repository.fetch()
            results.update(repository.getStatus())
        return results

    def getRepositories(self):
        return self.__repositories.values()

    def getRepository(self, name):
        return self.__repositories[name]
