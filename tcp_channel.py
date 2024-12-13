import logging
import socket
import threading
import time
from typing import Optional

from logging_lib.simple_logging.simple_logger import SimpleLogger

class TcpChannel:
    BYTES_FOR_DATA_SIZE = 4  # 2^(4*8)-1=4GB-1
    NEXT_READ_BYTES_LENGTH = 4096

    def __init__(self, logger: logging.Logger, listening_host, listening_port):
        self.logger = logger
        self.listening_host = listening_host
        self.listening_port = listening_port
        self.listening_thread = None
        self.data_receiving_thread = None
        self.is_listening = None
        self.is_data_receiving = None
        self.listening_socket = None
        self.client_socket: Optional[socket].socket = None
        self.client_address = None
        self.on_data_received_handler = None
        self.on_connection_error = None
        self.server_client_receiving_socket = None
        self.client_sending_socket = None
        self.channel_name = f"[{self.__class__.__name__} {self.listening_host}:{self.listening_port}]"

    def start_listening(self):
        self.logger.info(f"{self.channel_name} start listening")
        self.listening_thread = threading.Thread(target=self.listening_thread_handler, daemon=False)
        self.is_listening = True
        self.listening_thread.start()

    def _start_receiving(self):
        self.logger.info(f"{self.channel_name} start receiving")
        self.data_receiving_thread = threading.Thread(target=self.data_receiving_thread_handler, daemon=False)
        self.is_data_receiving = True
        self.data_receiving_thread.start()

    def register_data_received_callback(self, on_data_received_handler: callable):
        self.on_data_received_handler = on_data_received_handler

    def register_connection_error_callback(self, on_connection_error: callable):
        self.on_connection_error = on_connection_error

    def close(self):
        """close connection listener ,server_client_receiving_socket and client_sending_socket"""
        self.logger.info(f"{self.channel_name} closing")
        self.is_listening = False
        self.is_data_receiving = False
        if self.client_socket:
            self.client_socket.close()
        if self.listening_socket:
            self.listening_socket.close()

    def connect(self, remote_host, remote_port):
        self.logger.info(f"{self.channel_name} connecting to: [{remote_host}:{remote_port}]")
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((remote_host, remote_port))
        self.logger.info(f"{self.channel_name} connected to {self.client_socket.getpeername()} as {self.client_socket.getsockname()}")
        self._start_receiving()

    def send(self, data: bytes):
        data_length_bytes = len(data).to_bytes(TcpChannel.BYTES_FOR_DATA_SIZE, "big", signed=False)
        try:
            self.client_socket.sendall(data_length_bytes + data)
        except Exception as ex:
            self.logger.error(f"{self.channel_name} {ex}")
            if self.on_connection_error:
                self.on_connection_error(ex)

    def listening_thread_handler(self):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_socket.bind((self.listening_host, self.listening_port))
        self.listening_socket.listen(1)  # allow one client connection
        while self.is_listening:
            try:
                self.client_socket, self.client_address = self.listening_socket.accept()
                self.logger.info(f"{self.channel_name} accepted connection from client {self.client_address}")
                self._start_receiving()
            except OSError as ex:
                if ex.winerror == 10038:
                    self.logger.info(f"{self.channel_name} socket closed, stopped listening [WinError 10038]")
                    return
                self.logger.warning(f"{ex}")
            except Exception as ex:
                if self.is_listening:
                    self.logger.error(f"{ex}")
        self.logger.warning(f"{self.channel_name} listening thread terminated")

    def data_receiving_thread_handler(self):
        self.logger.debug(f"{self.channel_name} start receiving")
        while self.is_data_receiving:
            try:
                length_bytes = self.client_socket.recv(4)
                length = int.from_bytes(length_bytes, "big", signed=False)
                received_buffers = []
                while length > 0:
                    next_read = min(TcpChannel.NEXT_READ_BYTES_LENGTH, length)
                    buffer = self.client_socket.recv(next_read)
                    length -= next_read
                    received_buffers.append(buffer)
                data = b"".join(received_buffers)
                if data:
                    self.logger.debug(f"{self.channel_name} received data: {len(data)} bytes")
                    if self.on_data_received_handler:
                        self.on_data_received_handler(data)
            except OSError as ex:
                if ex.winerror == 10038:
                    self.logger.info(f"{self.channel_name} socket closed,stopped receiving [WinError 10038]")
                    return
                if self.is_data_receiving:
                    self.logger.error(f"{self.channel_name} {ex}")
                    if self.on_connection_error:
                        self.on_connection_error(ex)
                    return
            except Exception as ex:
                if self.is_data_receiving:
                    self.logger.error(f"{self.channel_name} {ex}")
                    if self.on_connection_error:
                        self.on_connection_error(ex)
                    return

if __name__ == '__main__':
    SimpleLogger("my_logger", logging.DEBUG)
    my_logger = logging.getLogger("my_logger")
    results = []

    def connect_send_receive():
        def on_data_received(data: bytes):
            my_logger.debug(f"*** received:{len(data)} bytes ***")
            results.append(len(data))
            results.append(data[0:2])

        results.clear()
        ch1 = TcpChannel(my_logger, "localhost", 9020)
        ch1.register_data_received_callback(on_data_received)
        ch1.start_listening()
        ch2 = TcpChannel(my_logger, "localhost", 9021)
        ch2.register_data_received_callback(on_data_received)
        ch2.start_listening()
        ch1.connect("localhost", 9021)
        time.sleep(0.1)
        ch1.send(b"12345678901" * 100 * 1024 * 1024)
        ch1.send(b"123456")
        ch2.send(b"abcdefgh")

        while len(results) < 6:
            time.sleep(.5)
        ch1.close()
        ch2.close()

        # verify received data
        print(results)
        assert results[0] == 8
        assert results[1] == b"ab"
        assert results[2] == 1153433600
        assert results[3] == b"12"
        assert results[4] == 6
        assert results[5] == b"12"

    def connection_error():
        ch1 = TcpChannel(my_logger, "localhost", 9020)
        ch1.start_listening()
        try:
            ch1.connect("localhost", 9021)
        except ConnectionRefusedError as ex:
            my_logger.error(f"expected error: {ex}")
        ch1.close()

    def connect_disconnect():
        def on_connection_error(ex: Exception):
            my_logger.info(f"****** {ex}")

        ch1 = TcpChannel(my_logger, "localhost", 9020)
        ch1.register_connection_error_callback(on_connection_error)
        ch1.start_listening()
        ch2 = TcpChannel(my_logger, "localhost", 9021)
        ch2.register_connection_error_callback(on_connection_error)
        ch2.start_listening()
        ch1.connect("localhost", 9021)
        ch1.send(b"123456")
        ch2.send(b"abcdefgh")
        time.sleep(0.5)
        # closing ch2 and sending
        ch2.close()
        ch1.send(b"12345678")
        # closing all
        ch1.close()

    connect_send_receive()
    connection_error()
    connect_disconnect()
