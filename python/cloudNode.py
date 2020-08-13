import logging
import math
import socket
import subprocess
import sys
import threading
import time
from io import BytesIO


def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        sock.settimeout(10.0)
        packet = sock.recv(n - len(data))
        if not packet:
            continue
        data.extend(packet)
    return data


def socketCopyToAndClose(src: socket.socket, dest, count):
    left = count
    while left != 0:
        readed = src.recv(left)
        if not readed:
            time.sleep(0.01)
            continue
        left -= len(readed)
        dest.write(readed)

    dest.close()


class CloudNode:
    def __init__(self, addr):
        self.addr = addr

    def start(self):
        t = threading.Thread(target=self._thread_client)
        t.start()

    def _thread_client(self):
        while True:
            try:
                clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                clientSocket.connect((self.addr, 39000))

                # Server is node-host?
                handshake = recvall(clientSocket, 5).decode()
                if handshake != "Node?":
                    logging.error(f"Handshake failure: {handshake}")
                    clientSocket.close()
                    return

                clientSocket.sendall('Yes!'.encode())
                logging.info(f"Connected to Host")

                while True:
                    logging.info(f"Receive Work Data")
                    dataLen = int.from_bytes(recvall(clientSocket, 4), byteorder='big')

                    logging.info(f"Processing...")
                    p = subprocess.Popen(['ffmpeg', '-f', 'mpegts', '-i', '-',
                                          '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'veryfast', '-f', 'mpegts', '-'],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                    copy = threading.Thread(target=socketCopyToAndClose, args=(clientSocket, p.stdin, dataLen,))
                    copy.start()
                    converted = p.stdout.read()

                    logging.info(f"Sending Result Data")
                    clientSocket.sendall('Done!'.encode())
                    clientSocket.sendall(len(converted).to_bytes(4, byteorder='big'))
                    clientSocket.sendall(converted)
            except Exception as ex:
                print(ex)
                print("Retry after 1 seconds")
                time.sleep(1)
