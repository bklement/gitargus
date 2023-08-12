from core import logging, Repository
from multiprocessing import Queue
from watchdog.events import FileSystemEventHandler
from jobs import RepositoryLocalUpdateJob


class RepositoryHandler(FileSystemEventHandler):

    def __init__(self, repository: Repository, queue: Queue):
        self.__repository = repository
        self.__queue = queue
        logging.debug(
            "Created handler for {}."
            .format(repository.name())
        )

    def on_any_event(self, event):
        logging.debug(
            "{} event recieved for {}."
            .format(event.event_type, event.src_path)
        )
        if (not event.is_directory
                and "/.#" not in event.src_path
                and ".git" not in event.src_path
                and event.event_type != "created"
                and not self.__repository.isIgnored(event.src_path)):
            logging.debug(
                "Creating RepositoryLocalUpdateJob for {}."
                .format(self.__repository.name())
            )
            job = RepositoryLocalUpdateJob(self.__repository)
            self.__queue.put(job)
            logging.debug(
                "RepositoryLocalUpdateJob for {} queued."
                .format(self.__repository.name())
            )
