"""
This module is responsible for communication with the server
"""
from p2p_fileshare.framework.messages import Message, MessageType


class Channel(object):
    def __init__(self, server_address: (str, int)):
        pass

    def send_msg_and_wait_for_response(self, message: Message):
        """
        Sends a message and wait for the server's response.
        :param message: The message to send.
        :return: A Message object containing the server's response.
        """
        raise NotImplementedError

    def _send_message(self, message: Message):
        raise NotImplementedError

    def _wait_for_response(self, expected_msg_type: MessageType, timeout=None):
        raise NotImplementedError
