from core import Workspace, Config, Dynamodb
import sys


config = Config()
workspace = Workspace(config.root(), config.repositories(), config.timezone())


def install():
    workspace.install()


def update(fetch: bool):
    print("update, fetch: ", fetch)
    Dynamodb(config.hostname(), config.table()).save(workspace.readRepositoryStatuses(fetch))


if __name__ == '__main__':
    if (sys.argv[1] == "install"):
        install()
    elif (sys.argv[1] == "update"):
        if (len(sys.argv) == 2):
            update(False)
        elif (sys.argv[2] == "--fetch"):
            update(True)
        else:
            print("Unrecognized option " + sys.argv[2])
    else:
        print("Unrecognized command " + sys.argv[1])
