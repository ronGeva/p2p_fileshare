"""
This module is a wrapper for reliable communication with an endpoint.
"""
import logging
import time

from p2p_fileshare.framework.messages import Message
from socket import socket
from struct import pack, unpack
from threading import Event
import select


logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    pass


class SocketClosedException(Exception):
    pass


class StopEventSignaledException(Exception):
    pass


class Channel(object):
    """
    An object wrapping an underlying socket and allowing communication with a remote endpoint via messages (objects
    inheriting from Message) as well as asynchronous message read/write with a timeout.

    The protocol used by the channel in order to transfer messages via a TCP stream is as follows:
        4 bytes of data - N
        N bytes of data - Message.
    """
    DEFAULT_TIMEOUT = 10

    def __init__(self, endpoint_socket: socket, stop_event: Event = None):
        self._socket = endpoint_socket
        self._is_socket_closed = False
        if stop_event is None:
            stop_event = Event()
        self._stop_event = stop_event

    def send_msg_and_wait_for_response(self, message: Message):
        """
        Sends a message and wait for the server's response.
        :param message: The message to send.
        :return: A Message object containing the server's response.
        """
        self.send_message(message)
        return self.wait_for_message(message.matching_response_type)

    def _get_data_from_sock(self, data_len, timeout: float):
        """
        Reads data from the socket until data_len bytes has been received or until the stop event has been signaled.
        @throws SocketClosedException if the socket is closed during the read operation.
        @throws StopEventSignaledException if the stop event is signaled during the read operation.
        """
        start_time = time.time()
        received_data = b''
        remaining_time = timeout - (time.time() - start_time)
        while len(received_data) != data_len and remaining_time > 0:
            if self._stop_event.is_set():
                raise StopEventSignaledException()

            rlist, _, _ = select.select([self._socket], [], [], remaining_time)
            if rlist:
                new_data = self._socket.recv(data_len-len(received_data))
                if len(new_data) == 0:
                    logger.debug('Got 0 bytes from socket, socket is closed')
                    self._is_socket_closed = True
                    raise SocketClosedException()
                received_data += new_data
            remaining_time = timeout - (time.time() - start_time)
        if len(received_data) == data_len:
            return received_data
        raise TimeoutException

    def send_message(self, message: Message):
        """
        Sends a single message via the channel.
        """
        if self._is_socket_closed:
            raise SocketClosedException()
        try:
            data = message.serialize()
            data_len = len(data)
            len_data = pack("I", data_len)
            full_message = len_data + data
            self._socket.send(full_message)
        except Exception as e:
            if self._stop_event.is_set():
                pass
            else:
                raise e

    def recv_message(self, timeout: float = DEFAULT_TIMEOUT) -> Message:
        """
        Receives a message from the underlying socket.
        :param timeout: The timeout of this function.
        :return: A message read by the channel.
        """
        start_time = time.time()
        if self._is_socket_closed:
            raise SocketClosedException()
        try:
            len_data = self._get_data_from_sock(4, timeout)
            msg_len = unpack("I", len_data)[0]
            msg_data = self._get_data_from_sock(msg_len, timeout - (time.time() - start_time))
            return Message.deserialize(msg_data)
        except Exception as e:
            if self._stop_event.is_set():
                pass
            else:
                raise e

    def wait_for_message(self, expected_msg_type: type, timeout: float = DEFAULT_TIMEOUT):
        """
        Waits for a message of a specific type to be received.
        Other messages that might arrive during this function's runtime will be ignored.
        :param expected_msg_type: The expected message type.
        :param timeout: The timeout of this method.
        :return: The message received.
        :raises: TimeoutException in case of a timeout.
        """
        # TODO: handle error message (so that if something failed the endpoint will know)
        start_time = time.time()
        while not self._stop_event.is_set() and time.time() - start_time < timeout:
            new_msg = self.recv_message(timeout - (time.time() - start_time))
            if isinstance(new_msg, expected_msg_type):
                return new_msg
        raise TimeoutException

    def fileno(self):
        return self._socket.fileno()

    def getpeername(self):
        return self._socket.getpeername()

    def close(self):
        self._stop_event.set()
        self._socket.close()
        self._is_socket_closed = True

    @property
    def closed(self):
        return self._is_socket_closed
