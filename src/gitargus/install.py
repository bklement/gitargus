import os
from gitargus.core import Config, CLI

config = Config(os.path.expanduser('~') + "/.gitargus/config.yml")
cli = CLI("/")

def hooks():
    for repository in config.repositories():
        filename = config.root() + "/" + repository + "/.git/hooks/pre-push"
        with open(filename, "w") as file:
            file.write("#!" + config.getProperty("python.bin") + "\n")
            file.write("from gitargus import hooks\n\n")
            file.write("hooks.pre_push()\n")
        cli.run(["chmod", "+x", filename])

def generateUbuntuServiceFile():
    with open("gitargus.service", "w") as file:
        file.write("[Unit]\n")
        file.write("Description=GitArgus daemon\n\n")
        file.write("[Service]\n")
        file.write("User=" + config.getProperty("user") + "\n")
        file.write("ExecStart=" + config.getProperty("python.bin") + " -m gitargus\n")
        file.write("Restart=always\n\n")
        file.write("[Install]\n")
        file.write("WantedBy=multi-user.target\n")
