import logging
import socket
import threading
from typing import Optional

class TcpChannel:
    BYTES_FOR_DATA_SIZE = 4
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
