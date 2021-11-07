"""
This module is a wrapper for reliable communication with an endpoint.
"""
from p2p_fileshare.framework.messages import Message
from socket import socket
from struct import pack, unpack


class Channel(object):
    def __init__(self, endpoint_socket: socket):
        self._socket = endpoint_socket

    def send_msg_and_wait_for_response(self, message: Message):
        """
        Sends a message and wait for the server's response.
        :param message: The message to send.
        :return: A Message object containing the server's response.
        """
        self.send_message(message)
        return self.wait_for_message(message.matching_response_type)

    def send_message(self, message: Message):
        data = message.serialize()
        data_len = len(data)
        len_data = pack("I", data_len)
        full_message = len_data + data
        self._socket.send(full_message)

    def recv_message(self):
        len_data = self._socket.recv(4)
        msg_len = unpack("I", len_data)[0]
        msg_data = self._socket.recv(msg_len)
        return Message.deserialize(msg_data)

    def wait_for_message(self, expected_msg_type: type, timeout=None):
        while True:  # TODO: implement stop condition
            new_msg = self.recv_message()
            if isinstance(new_msg, expected_msg_type):
                return new_msg

    def fileno(self):
        return self._socket.fileno()

    def getsockname(self):
        return self._socket.getsockname()
