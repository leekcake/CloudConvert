import logging
import sys

from python.cloudNode import CloudNode

if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    root.addHandler(handler)

    node = CloudNode("localhost")
    node.start()
    pass