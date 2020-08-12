import logging
import math
import os
import socket
import subprocess
import sys
import threading
import time
import uuid


def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            continue
        data.extend(packet)
    return data


def get_length(input_video):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
         input_video], stdout=subprocess.PIPE)  # , stderr=sys.stderr.buffer
    return float(result.stdout)


def get_data(src, inx):
    result = subprocess.run(
        ['ffmpeg', '-i', src, '-ss', str(inx * 60), '-t', '60', '-c', 'copy', '-f', 'mpegts', '-'],
        stdout=subprocess.PIPE)
    return result.stdout


class Processor:
    def __init__(self):
        self.workInx = -1
        self.workData: bytes = None
        self.InWork = False
        self.outputData: bytes = None
        self.isFinish = False

    def clearProcessor(self):
        self.workInx = -1
        self.InWork = False
        self.workData = None
        self.outputData = None
        self.isFinish = False

    def provideNewWork(self, inx, data):
        if self.InWork:
            raise Exception("Processor already in work")
        self.InWork = True
        self.workData = data
        self.workInx = inx

    def clearWorkData(self):
        self.workData = None

    def markAsFinished(self, result):
        self.isFinish = True
        self.outputData = result

    def isMarkedAsFinished(self):
        return self.isFinish

    def isIdle(self):
        return self.workInx == -1

    def isCanStartWork(self):
        return self.InWork and self.workData is not None


class CloudServer:
    def __init__(self):
        self.started = False
        self.processors = []
        self.workInxs = []
        self.preload = {}
        self.doneData = {}
        self.doneInxs = {}
        self.lock = threading.Lock()
        self.clientSockets = []

    def startServer(self):
        self.started = True
        t = threading.Thread(target=self._thread_server)
        t.start()

    def registerProcessor(self, processor):
        self.lock.acquire()
        self.processors.append(processor)
        self.lock.release()

    def unregisterProcessor(self, processor):
        self.lock.acquire()
        if processor.InWork:
            logging.info(f"Work Inx: {processor.workInx} was re-requested because gone of processor")
            # if processor leave without finish work, re-register work
            self.workInxs.insert(0, processor.workInx)
        self.processors.remove(processor)
        self.lock.release()

    def _thread_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("", 39000))
        logging.info("Server bind in 39000")
        server_socket.listen()
        while True:
            client_socket, addr = server_socket.accept()
            self.clientSockets.append(client_socket)
            t = threading.Thread(target=self._thread_client, args=(client_socket, addr,))
            t.start()


    def _thread_preload(self, src):
        while True:
            for workInx in self.workInxs[:21]:
                if workInx not in self.preload:
                    self.preload[workInx] = get_data(src, workInx)

            time.sleep(1)

    def _thread_client(self, clientSocket: socket.socket, addr):
        name = str(addr)
        try:
            clientSocket.sendall('Node?'.encode())

            # It's not valid node :(
            handshake = clientSocket.recv(4).decode()
            if handshake != 'Yes!':
                logging.error(f"Handshake failure: {handshake}")
                clientSocket.close()
                self.clientSockets.remove(clientSocket)
                return
        except:
            self.clientSockets.remove(clientSocket)
            return

        logging.info(f"New node({name}) connected")

        # We found valid node, register self as processor
        processor = Processor()
        self.registerProcessor(processor)

        try:
            while True:
                # Work not provided yet?
                if not processor.isCanStartWork():
                    time.sleep(1)
                    continue

                logging.info(f"{name}: Send work")
                # Start work data size
                clientSocket.sendall(len(processor.workData).to_bytes(4, byteorder='big'))
                # Send work data
                clientSocket.sendall(processor.workData)
                processor.clearWorkData()

                logging.info(f"{name}: Wait for result")
                # Wait for done response
                if recvall(clientSocket, 5).decode() != 'Done!':
                    # Normally, Node must retries on error
                    # No client response is not Done!, is something problem on client
                    # So close it.
                    clientSocket.close()
                    break

                bufferLen = int.from_bytes(recvall(clientSocket, 4), byteorder='big')
                processor.markAsFinished(recvall(clientSocket, bufferLen))

                logging.info(f"{name}: Received {bufferLen} data.")

                # Yey, work was finished! wait for checkout from merger

        except Exception as e:
            print(e)
            pass

        try:
            clientSocket.close()
        except:
            pass
        self.clientSockets.remove(clientSocket)
        logging.info(f"{name}: disconnected")
        self.unregisterProcessor(processor)

    def convert(self, src, dest):
        if not self.started:
            raise Exception("convert before startServer")

        t = threading.Thread(target=self._thread_preload, args=(src,))
        t.start()

        # Get Duration from file and make work inxs
        duration = get_length(src)
        maxInx = math.floor(duration / 60)

        for inx in range(maxInx + 1):
            self.workInxs.append(inx)

        # Open ffmpeg for combine
        pp = subprocess.Popen(['ffmpeg', '-f', 'mpegts', '-i', 'pipe:', "-c", "copy", "-y", dest],
                              stdout=sys.stdout.buffer,
                              stdin=subprocess.PIPE, stderr=sys.stderr.buffer)

        pushInx = 0
        while True:
            for processor in self.processors:
                # If processor finished work and waiting for done
                if processor.isMarkedAsFinished():
                    if processor.workInx in self.doneInxs:
                        logging.info(
                            f"Receive work result but already done by another node, number {processor.workInx}")
                    else:
                        logging.info(f"Receive work result, number {processor.workInx}")
                        self.doneData[processor.workInx] = processor.outputData
                        self.doneInxs[processor.workInx] = True
                        del (self.preload[processor.workInx])

                    processor.clearProcessor()

                # If no work left or can't provide work in now, prevent provide work
                if len(self.workInxs) != 0 and self.workInxs[0] not in self.preload:
                    continue

                # If processor didn't have any work
                if processor.isIdle():
                    # Provide work
                    workInx = -1
                    if len(self.workInxs) == 0:
                        proc: Processor
                        for proc in self.processors:
                            if not proc.isIdle() and proc.workInx in self.preload:
                                workInx = proc.workInx
                        if workInx == -1:
                            continue
                    else:
                        workInx = self.workInxs.pop(0)
                    processor.provideNewWork(workInx, self.preload[workInx])

            # Push to ffmpeg,
            while True:
                if pushInx in self.doneData:
                    pp.stdin.write(self.doneData[pushInx])
                    del (self.doneData[pushInx])
                    pushInx += 1
                else:
                    break

            if pushInx == maxInx + 1:
                break

            time.sleep(0.1)

        pp.stdin.close()
        pp.wait()

        for sock in self.clientSockets:
            sock.close()
