from gitargus.jobs import WorkspaceFullUpdateJob, JobRunner
from gitargus.core import Workspace, Config, WORK_DIR, logging
from gitargus.persistence import Dynamodb
from gitargus.handler import RepositoryHandler
from gitargus.messaging import SQSListener
from watchdog.observers import Observer
import time
from multiprocessing import Queue, Process


class Daemon():

    def __init__(self, initialUpdate: bool, sqsPurge: bool):
        self.__config = Config(WORK_DIR + "/config.yml")
        self.__workspace = Workspace(
            self.__config.root(),
            self.__config.repositories(),
            self.__config.timezone()
        )
        self.__queue = Queue(100)
        self.__initialUpdate = initialUpdate
        self.__sqsPurge = sqsPurge

    def __createJobRunnerProcess(self):
        jobRunner = JobRunner(
            WORK_DIR,
            self.__queue,
            Dynamodb(self.__config.hostname(), self.__config.table())
        )
        jobRunner.removeLock()
        runnerProcess = Process(target=jobRunner.start)
        runnerProcess.start()
        return runnerProcess

    def __createListenerProcess(self):
        sqsListener = SQSListener(
            self.__config.hostname(),
            self.__workspace,
            self.__queue,
            self.__config.queue()
        )
        listenerProcess = Process(target=sqsListener.listen)
        if self.__sqsPurge:
            sqsListener.purge()
        listenerProcess.start()
        return listenerProcess
    
    def __createObserver(self):
        observer = Observer()
        for repository in self.__workspace.getRepositories():
            observer.schedule(
                RepositoryHandler(repository, self.__queue),
                self.__config.root() + "/" + repository.name(),
                recursive=True
            )
        observer.start()
        return observer

    def start(self):
        logging.info("Daemon starting.")
        runnerProcess = self.__createJobRunnerProcess()
        if self.__initialUpdate:
            self.__queue.put(WorkspaceFullUpdateJob(self.__workspace))
        listenerProcess = self.__createListenerProcess()
        observer = self.__createObserver()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()

        observer.join()
        listenerProcess.join()
        runnerProcess.join()
        logging.info("Daemon exited.")
