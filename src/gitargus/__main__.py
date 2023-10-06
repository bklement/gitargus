from .core import Workspace, Config, Dynamodb


def run():
    config = Config()
    dynamodb = Dynamodb(config.hostname(), config.table())
    workspace = Workspace(config.root(), config.repositories(), config.timezone())
    dynamodb.save(workspace.readRepositoryStatuses())


if __name__ == '__main__':
    run()
