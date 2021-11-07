"""
A module containing the "Server" class.
The server class implements server socket initialization, client acceptance logic, and the creation of new
communication channels.
"""
import socket
import logging
from channel import ClientChannel
from db_manager import DBManager
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.server import Server


logger = logging.getLogger(__file__)
MAX_PENDING_CLIENTS = 5  # TODO: make this configurable


class MetadataServer(Server):
    def __init__(self):
        super().__init__()
        self._communication_channels = []
        self._db = DBManager()

    def _receive_new_client(self, client: socket.socket, client_address: tuple[str, int]):
        new_channel = Channel(client)
        new_comm_channel = ClientChannel(new_channel, self._db, self.get_all_clients_info)
        self._communication_channels.append(new_comm_channel)

    def _remove_old_clients(self):
        """
        Removes invalid communication channels from the list.
        """
        remove_list = []
        for communication_channel in self._communication_channels:
            if not communication_channel.is_active:
                remove_list.append(communication_channel)
        for item in remove_list:
            logger.debug("Removing inactive channel with client {}".format(item.get_client_connection_info()[0]))
            self._communication_channels.remove(item)

    def get_all_clients_info(self):
        return [channel.get_client_connection_info() for channel in self._communication_channels]
