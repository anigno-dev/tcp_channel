import logging
import time

from simple_logging.simple_logger import SimpleLogger
from tcp_channel import TcpChannel

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
