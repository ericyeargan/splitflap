import serial

import socket
import requests

class SerialTransport(object):
    def __init__(self, device, baud_rate):
        self._serial = None
        self._device = device
        self._baud_rate = baud_rate

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        self._serial = serial.Serial(self._device, self._baud_rate)

    def close(self):
        if self._serial is not None:
            self._serial.close()

    def readline(self):
        return self._serial.readline().decode('utf-8')

    def write(self, data):
        return self._serial.write(data.encode('utf-8'))


class EspLinkTransport(object):
    def __init__(self, host):
        self._socket = None
        self._host = host

    def __enter__(self):
        self.open()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._socket.close()

    def open(self):
        self._open_socket()

        requests.post(f'http://{self._host}/console/reset')

    def close(self):
        if self._socket is not None:
            self._socket.close()

    def _open_socket(self):
        self.close()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, 23))

    def readline(self):
        line_buf = ''
        eol = False
        while not eol:
            byte_buf = self._socket.recv(1)
            if len(byte_buf) == 0:
                self._open_socket()
                byte_buf = self._socket.recv(1)

            char_buf = byte_buf.decode('utf-8')
            line_buf += char_buf
            if char_buf[0] == '\n':
                eol = True

        return line_buf

    def write(self, string):
        byte_buf = string.encode('utf-8')
        self._socket.send(byte_buf)
