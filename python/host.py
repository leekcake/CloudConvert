import logging
import sys
import time

from python.cloudServer import CloudServer
from python.selfNode import SelfNode

if __name__ == '__main__':
    In = sys.argv[1]
    Out = sys.argv[2]
    SelfNodeCount = 0
    if len(sys.argv) > 3:
        SelfNodeCount = int(sys.argv[3])

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    root.addHandler(handler)

    server = CloudServer()
    server.startServer()

    while SelfNodeCount != 0:
        node = SelfNode()
        node.attachToServer(server)
        node.start()
        SelfNodeCount -= 1

    server.convert(In, Out)