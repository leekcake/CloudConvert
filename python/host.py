import logging
import sys
import time

from python.cloudServer import CloudServer

if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    root.addHandler(handler)

    server = CloudServer()
    server.startServer()
    start = time.time()
    server.convert(sys.argv[1], sys.argv[2])
    print(f"Convert time in seconds: {time.time() - start}")