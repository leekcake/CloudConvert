import logging
import socket
import subprocess
import sys
import threading
from io import BytesIO


def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            continue
        data.extend(packet)
    return data


def convert_data(data):
    # p = subprocess.Popen(['ffmpeg', '-i', 'pipe:', '-c:v', 'libx264', '-f', 'h264', 'pipe:']
    #                     , stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=sys.stderr.buffer)
    # p.stdin.write(data)
    # p.stdin.close()
    # result = p.stdout.read()
    p = subprocess.run(['ffmpeg', '-f', 'h264', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-f', 'h264', '-'],
                       stdout=subprocess.PIPE, input=data)  # , stderr=sys.stderr.buffer

    return p.stdout


class CloudNode:
    def __init__(self, addr):
        self.addr = addr

    def start(self):
        t = threading.Thread(target=self._thread_client)
        t.start()

    def _thread_client(self):
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
            data = clientSocket.recv(dataLen)
            logging.info(f"Receive Work Data: {dataLen}")

            logging.info(f"Processing...")
            converted = convert_data(data)

            logging.info(f"Sending Result Data")
            clientSocket.sendall('Done!'.encode())
            clientSocket.sendall(len(converted).to_bytes(4, byteorder='big'))
            clientSocket.sendall(converted)
