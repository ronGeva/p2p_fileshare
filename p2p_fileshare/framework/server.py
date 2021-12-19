"""
A general purpose server module which implements the server's main loop (check for new clients and remove inactive
clients).
"""
import socket
import logging
from abc import ABC, abstractmethod
from select import select
from typing import Callable, Any
from p2p_fileshare.framework.selectable_event import generate_socket_pair, signal


logger = logging.getLogger(__file__)
MAX_PENDING_CLIENTS = 5


class StopException(Exception):
    pass


class Server(ABC):
    WAIT_TIMEOUT = 1

    def __init__(self, port=0):
        self._socket = socket.socket()
        self._socket.bind(('0.0.0.0', port))
        self._socket.listen(MAX_PENDING_CLIENTS)
        logger.debug(f"Starting server at address: {self._socket.getsockname()}")
        self._selectable_sockets = {self._socket: self._accept_new_client}  # type: dict[socket.socket, Callable]
        stop_event_provider, stop_event_consumer = generate_socket_pair(self._socket)
        self._stop_provider = stop_event_provider
        self._selectable_sockets[stop_event_consumer] = self._stop
        self._items = []  # type is decided by derived class

    @abstractmethod
    def _receive_new_client(self, client: socket.socket, client_address: tuple[str, int],
                            finished_socket: socket.socket) -> Any:
        """
        Receives a new client and returns it.
        """
        pass

    def _accept_new_client(self):
        """
        Checks for a new client and create an appropriate channel for it.
        :return: None.
        """
        new_client, client_address = self._socket.accept()
        logger.debug(f"Accepted new client: {client_address}")
        finished_provider, finished_consumer = generate_socket_pair(self._socket)
        new_item = self._receive_new_client(new_client, client_address, finished_provider)
        self._items.append(new_item)
        self._selectable_sockets[finished_consumer] = lambda: self.remove_client(finished_consumer, new_item)

    def remove_client(self, consuming_socket: socket.socket, item: Any):
        consuming_socket.recv(1)  # read the single byte message
        self._selectable_sockets.pop(consuming_socket)
        self._items.remove(item)

    def _stop(self):
        """
        Causes the main_loop to exit by raising pre-defined exception.
        """
        raise StopException

    def stop(self):
        signal(self._stop_provider)
        logger.debug("Server's stop event was set!")

    def main_loop(self):
        try:
            while True:
                rlist, _, _ = select(self._selectable_sockets.keys(), [], [])  # infinite wait
                for selectable in rlist:
                    self._selectable_sockets[selectable]()
        except StopException:
            logger.debug("Server has exited main_loop!")
