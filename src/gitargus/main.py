from jobs import WorkspaceFullUpdateJob, JobRunner
from core import Workspace, Config, WORK_DIR, logging
from persistence import Dynamodb
from watchdog.observers import Observer
import time
from multiprocessing import Queue, Process
from handler import RepositoryHandler
from messaging import SQSListener

if __name__ == '__main__':
    logging.info("Daemon starting.")
    config = Config(WORK_DIR + "/config.yml")
    workspace = Workspace(config.root(), config.repositories(), config.timezone())
    queue = Queue(100)

    jobRunner = JobRunner(WORK_DIR, queue, Dynamodb(config.hostname(), config.table()))
    jobRunner.removeLock()
    runnerProcess = Process(target=jobRunner.start)
    runnerProcess.start()

    queue.put(WorkspaceFullUpdateJob(workspace))

    listenerProcess = Process(target=SQSListener(config.hostname(), workspace, queue, config.queue()).listen)
    listenerProcess.start()

    observer = Observer()
    for repository in workspace.getRepositories():
        observer.schedule(RepositoryHandler(repository, queue), config.root() + "/" + repository.name(), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    listenerProcess.join()
    runnerProcess.join()
    logging.info("Daemon exited.")
    









