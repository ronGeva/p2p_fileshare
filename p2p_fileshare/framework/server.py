"""
A general purpose server module which implements the server's main loop (check for new clients and remove inactive
clients).
"""

"""
A module containing the "Server" class.
The server class implements server socket initialization, client acceptance logic, and the creation of new
communication channels.
"""
import socket
import logging
from abc import ABC, abstractmethod
from select import select


logger = logging.getLogger(__file__)
MAX_PENDING_CLIENTS = 5  # TODO: make this configurable


class Server(ABC):
    def __init__(self):
        self._socket = socket.socket()
        self._socket.bind(('0.0.0.0', 0))
        self._socket.listen(MAX_PENDING_CLIENTS)
        logger.debug("Starting server at address: {}".format(self._socket.getsockname()))

    @abstractmethod
    def _receive_new_client(self, client: socket.socket, client_address: tuple[str, int]):
        pass

    def _check_for_new_clients(self):
        """
        Checks for a new client and create an appropriate channel for it.
        :return: None.
        """
        rlist, _, _ = select([self._socket], [], [], 0)
        if rlist:
            new_client, client_address = self._socket.accept()
            logger.debug("Accepted new client: {}".format(client_address))
            self._receive_new_client(new_client, client_address)

    @abstractmethod
    def _remove_old_clients(self):
        """
        Removes invalid communication channels from the list.
        """
        pass

    def main_loop(self):
        # TODO: this method performs a busy wait which is very inefficient. This was done since Windows does not support
        # using "select" on non-socket file descriptors, which made it hard for us to properly realize when a client
        # channel has crashed without iterating through them all
        self._check_for_new_clients()
        self._remove_old_clients()
