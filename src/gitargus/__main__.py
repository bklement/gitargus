from gitargus.daemon import Daemon
from gitargus.hooks import install

install()
Daemon(True, True).start()