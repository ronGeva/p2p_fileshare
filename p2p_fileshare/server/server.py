"""
A module containing the "Server" class.
The server class implements server socket initialization, client acceptance logic, and the creation of new
communication channels.
"""
import socket
import logging
from select import select
from channel import ClientChannel
from db_manager import DBManager
from p2p_fileshare.framework.channel import Channel


logger = logging.getLogger(__file__)
MAX_PENDING_CLIENTS = 5  # TODO: make this configurable


class Server(object):
    def __init__(self):
        self._socket = socket.socket()
        self._socket.bind(('0.0.0.0', 0))
        self._socket.listen(MAX_PENDING_CLIENTS)
        logger.debug("Starting server at address: {}".format(self._socket.getsockname()))
        self._communication_channels = []
        self._db = DBManager()

    def _check_for_new_clients(self):
        """
        Checks for a new client and create an appropriate channel for it.
        :return:
        """
        rlist, _, _ = select([self._socket], [], [], 0)
        if rlist:
            new_client, client_address = self._socket.accept()
            logger.debug("Accepted new client: {}".format(client_address))
            new_channel = Channel(new_client)
            new_comm_channel = ClientChannel(new_channel, self._db)
            self._communication_channels.append(new_comm_channel)

    def _remove_old_clients(self):
        """
        Removes invalid communication channels from the list.
        """
        pass

    def main_loop(self):
        self._check_for_new_clients()
        self._remove_old_clients()
