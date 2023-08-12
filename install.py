import os
from gitargus.core import Config, CLI

config = Config(os.path.expanduser('~') + "/.gitargus/config.yml")

pythonPath = CLI("/").run(["which", "python3"])
print(pythonPath)

for repository in config.repositories():
    f = open(config.root() + "/" + repository + "/.git/hooks/pre-push", "w")
    f.write("#!" + pythonPath)
    f.write("from gitargus import hooks\n\n")
    f.write("hooks.pre_push()\n")
    f.close()