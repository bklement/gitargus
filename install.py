import os
from gitargus.core import Config, CLI

config = Config(os.path.expanduser('~') + "/.gitargus/config.yml")

for repository in config.repositories():
    filename = config.root() + "/" + repository + "/.git/hooks/pre-push"
    f = open(filename, "w")
    f.write("#!" + config.getProperty("python.bin") + "\n")
    f.write("from gitargus import hooks\n\n")
    f.write("hooks.pre_push()\n")
    f.close()
    CLI("/").run(["chmod", "+x", filename])