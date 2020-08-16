import logging
import socket
import subprocess
import threading
import time

from python.cloudServer import Processor


def memoryToffmpeg(In, Out):
    try:
        Out.write(In)
        Out.flush()
        Out.close()
    except Exception as e:
        logging.exception(e)


class SelfNode:
    def __init__(self):
        self.processor = Processor()

    def attachToServer(self, server):
        server.registerProcessor(self.processor)

    def start(self):
        t = threading.Thread(target=self.selfNode)
        t.start()

    def selfNode(self):
        while True:
            p = None
            try:
                if not self.processor.isCanStartWork():
                    time.sleep(0.1)
                    continue
                p = subprocess.Popen(['ffmpeg', '-f', 'mpegts', '-i', '-',
                                      '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'veryfast', '-f', 'mpegts', '-'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                copy = threading.Thread(target=memoryToffmpeg, args=(self.processor.workData, p.stdin,))
                copy.start()
                converted = p.stdout.read()
                p.stdout.close()
                p.wait()

                self.processor.markAsFinished(converted)
            except Exception as e:
                logging.exception(e)
                try:
                    p.kill()
                except:
                    pass
