# TCP Channel

## This Python class TcpChannel implements a TCP communication channel with multithreading, enabling the creation of a TCP server or client that can send and receive data asynchronously. Below is a breakdown of the class and its components:

## Class Overview
TcpChannel is a class designed to:

Start a server to listen for incoming TCP connections.
Connect to a remote server as a client.
Send and receive data using TCP sockets.
Use callbacks for handling received data or connection errors.
Log operations for easier debugging and tracking.

## Key Attributes
Constants:

BYTES_FOR_DATA_SIZE: Specifies the number of bytes used to encode the size of the data being sent.
NEXT_READ_BYTES_LENGTH: Defines the buffer size for receiving data.
Constructor (__init__):

Sets up logger, host, port, threading variables, and socket placeholders.
Initializes callbacks for handling received data and errors.
Generates a unique channel_name for logs.

## Methods

1. start_listening()
Starts a listening thread that accepts incoming connections.
Used when the channel acts as a server.
2. _start_receiving()
Starts a thread for receiving data from the connected client.
Automatically called when a connection is established.
3. register_data_received_callback()
Registers a callback for handling received data.
Callback signature: on_data_received_handler(data: bytes).
4. register_connection_error_callback()
Registers a callback for handling connection errors.
Callback signature: on_connection_error(error: Exception).
5. close()
Closes sockets and stops the listening and receiving threads.
6. connect()
Connects to a remote server as a client.
Starts the receiving thread after connecting.
7. send()
Sends data to the connected peer.
Prepends the data with its length (in bytes) for easier framing during reception.
8. listening_thread_handler()
Handles the listening thread:
Binds the socket to a host and port.
Listens for incoming connections.
Accepts one client connection at a time.
9. data_receiving_thread_handler()
Handles the data receiving thread:
Reads the length of the incoming message.
Reads the message in chunks and reassembles it.
Passes the received data to the registered callback.
Error Handling
WinError 10038: Specific to Windows, occurs when a socket operation is attempted on a closed socket.
Handles OSError and general exceptions during listening and data reception.
Calls on_connection_error callback if an error occurs.
Logging
Logs every significant action or error to help monitor the state of the channel.
Includes details like connection status, received data size, and errors.

## Advantages
Multithreading: Handles listening and receiving concurrently.
Callbacks: Decouples logic for handling data and errors.
Framing: Sends and receives data with size headers for better handling.


# example.py
This script demonstrates various functionalities of the TcpChannel class through three test scenarios: sending/receiving data, handling connection errors, and managing connections/disconnections. Below is an explanation of its components and functionality:

Imports
logging: For logging events and debug information.
time: To introduce delays for synchronization.
simple_logging.simple_logger: A custom logger setup utility.
TcpChannel: The TcpChannel class for TCP communication.
Logger Setup
SimpleLogger("my_logger", logging.DEBUG):
Configures a logger named my_logger with a debug level.
my_logger = logging.getLogger("my_logger"):
Retrieves the logger instance for use throughout the script.
Global Variables
results: A list used to store data received during communication tests.
Test Scenarios
1. connect_send_receive()
This function tests sending and receiving data between two TcpChannel instances.

Callbacks:

on_data_received(data: bytes):
Appends the size and first two bytes of the received data to the results list.
Logs the size of the received data.
Channels Setup:

Two TcpChannel instances (ch1 and ch2) are created, bound to ports 9020 and 9021, respectively.
Both channels register the on_data_received callback.
ch1 connects to ch2.
Sending Data:

ch1 sends:
A large message (1 GB of repeated data).
A small message (b"123456").
ch2 sends b"abcdefgh".
Wait and Verify:

The script waits until six results are collected in results.
The channels are closed, and the received data is validated using assertions:
The first received message is 8 bytes with b"ab".
The second received message is the large data size and starts with b"12".
The third received message is 6 bytes with b"12".
2. connection_error()
This function tests handling of a connection error.

Setup:

ch1 listens on port 9020.
An attempt is made to connect ch1 to a non-existent server on port 9021.
Error Handling:

A ConnectionRefusedError is expected because no server is listening on port 9021.
The error is logged using the logger.
Teardown:

ch1 is closed.
3. connect_disconnect()
This function tests behavior when a peer disconnects during communication.

Callbacks:

on_connection_error(ex: Exception):
Logs connection errors as they occur.
Channels Setup:

Two TcpChannel instances (ch1 and ch2) are created, bound to ports 9020 and 9021, respectively.
Both channels register the on_connection_error callback.
ch1 connects to ch2.
Sending Data:

ch1 sends b"123456".
ch2 sends b"abcdefgh".
Peer Disconnect:

ch2 is closed while communication is ongoing.
ch1 attempts to send more data (b"12345678") and triggers a connection error.
Teardown:

Both channels are closed.
Execution
connect_send_receive():
Tests bi-directional communication and verifies received data.
connection_error():
Simulates and logs a connection error when attempting to connect to a non-existent server.
connect_disconnect():
Demonstrates graceful handling of a peer disconnection during communication.
Key Features Demonstrated
Asynchronous Communication:
Sending and receiving are handled concurrently using threads.
Callbacks:
Customizable behavior for data reception and error handling.
Error Handling:
Graceful handling and logging of connection errors.
Data Integrity:
Ensures that sent data matches received data, validating transmission integrity.
Output
The script logs all events, including data transfer sizes, connection statuses, errors, and disconnections. Assertions in connect_send_receive() validate the correctness of data transmission.