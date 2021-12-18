"""
A general purpose server module which implements the server's main loop (check for new clients and remove inactive
clients).
"""
import socket
import logging
from abc import ABC, abstractmethod
from select import select


logger = logging.getLogger(__file__)
MAX_PENDING_CLIENTS = 5


class Server(ABC):
    WAIT_TIMEOUT = 1

    def __init__(self, port=0):
        self._socket = socket.socket()
        self._socket.bind(('0.0.0.0', port))
        self._socket.listen(MAX_PENDING_CLIENTS)
        logger.debug(f"Starting server at address: {self._socket.getsockname()}")
        self._should_stop = False

    @abstractmethod
    def _receive_new_client(self, client: socket.socket, client_address: tuple[str, int]):
        pass

    def _accept_new_client(self):
        """
        Checks for a new client and create an appropriate channel for it.
        :return: None.
        """
        new_client, client_address = self._socket.accept()
        logger.debug(f"Accepted new client: {client_address}")
        self._receive_new_client(new_client, client_address)

    @abstractmethod
    def _remove_old_clients(self):
        """
        Removes invalid communication channels from the list.
        """
        pass

    def stop(self):
        self._should_stop = True
        logger.debug("Server's stop event was set!")

    def main_loop(self):
        while not self._should_stop:
            rlist, _, _ = select([self._socket], [], [], self.WAIT_TIMEOUT)
            if rlist:
                self._accept_new_client()
            self._remove_old_clients()
        logger.debug("Server has exited main_loop!")
