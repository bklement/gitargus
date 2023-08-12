import os
from abc import ABC, abstractmethod
import urllib.request
from gitargus.core import Workspace, Repository, logging, WORK_DIR
from gitargus.persistence import Database
from multiprocessing import Queue
import time


class Job(ABC):

    def __init__(self):
        try:
            urllib.request.urlopen("http://github.com")
        except Exception as e:
            logging.warning("No internet connection, skipping iteration.")
            print(e, flush=True)
            exit(1)

    @abstractmethod
    def run(self, database: Database):
        pass


class JobRunner():

    LOCK_FILE = WORK_DIR + "/git-watcher.lock"

    def __init__(self, workDir: str, queue: Queue, database: Database):
        self.__database = database
        self.__queue = queue
        self.__lockFile = workDir + "/git-watcher.lock"
        logging.debug("JobRunner created.")

    def removeLock(self):
        if os.path.isfile(self.__lockFile):
            logging.debug("Removing lock file.")
            os.remove(self.__lockFile)
            logging.debug("Lock file removed.")

    def __createLock(self):
        while True:
            try:
                logging.debug("Creating lock file.")
                open(self.__lockFile, "x").close()
                break
            except FileExistsError:
                logging.debug("Lock file already exists, sleeping.")
                time.sleep(1)

    def __execute(self, job: Job):
        try:
            self.__createLock()
            logging.debug("Lock file created, starting job.")
            job.run(self.__database)
        except Exception as e:
            logging.error(e)
        finally:
            self.removeLock()

    def start(self):
        logging.debug("Starting JobRunner.")
        while True:
            logging.debug("Polling for job.")
            job = self.__queue.get()
            if job is None:
                break
            logging.debug("Job received, executing")
            self.__execute(job)


class WorkspaceUpdateJob(Job):

    def __init__(self, workspace: Workspace, fetch: bool):
        super().__init__()
        self.__workspace = workspace
        self.__fetch = fetch

    def run(self, database: Database):
        logging.info("Iteration started.")
        results = self.__workspace.readRepositoryStatuses(self.__fetch)
        logging.info("Saving results to database.")
        database.save(results)
        logging.info("Success.")
        logging.info("Iteration finished.")


class WorkspaceLocalUpdateJob(WorkspaceUpdateJob):

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, False)
        logging.debug("WorkspaceLocalUpdateJob created.")


class WorkspaceFullUpdateJob(WorkspaceUpdateJob):

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, True)
        logging.debug("WorkspaceFullUpdateJob created.")


class RepositoryUpdateJob(Job):

    def __init__(self, repository: Repository, fetch: bool):
        super().__init__()
        self.__repository = repository
        self.__fetch = fetch

    def run(self, database: Database):
        logging.info(
            "Updating repository {}."
            .format(self.__repository.name())
        )
        if self.__fetch:
            self.__repository.fetch()
        results = self.__repository.getStatus()
        logging.info("Saving results to database.")
        database.update(self.__repository.name(), results)
        logging.info("Success.")


class RepositoryLocalUpdateJob(RepositoryUpdateJob):

    def __init__(self, repository: Repository):
        super().__init__(repository, False)
        logging.debug(
            "RepositoryLocalUpdateJob created for {}."
            .format(repository.name())
        )


class RepositoryFullUpdateJob(RepositoryUpdateJob):

    def __init__(self, repository: Repository):
        super().__init__(repository, True)
        logging.debug(
            "RepositoryFullUpdateJob created for {}."
            .format(repository.name())
        )
