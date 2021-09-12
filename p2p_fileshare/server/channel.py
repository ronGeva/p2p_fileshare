"""
A module containing the communication channel logic.
Each communication channel represents a single channel between the server and a client.
All actions in the channel must be made in a thread-safe way to ensure no data corruption is taking place.
"""
from threading import Thread


class CommunicationChannel(object):
    def __init__(self, client_socket):
        self._client_socket = client_socket
        self._thread = Thread(target=self.__start)
        self._thread.start()

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        raise NotImplementedError

    def __stop(self):
        """
        Stops the channel's thread and signal the main Server component that this channel is invalid.
        """
        raise NotImplementedError
