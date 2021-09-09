"""
A module containing the communication channel logic.
Each communication channel represents a single channel between the server and a client.
All actions in the channel must be made in a thread-safe way to ensure no data corruption is taking place.
"""


class CommunicationChannel(object):
    def __init__(self, client_socket):
        self._client_socket = client_socket
