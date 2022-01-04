"""
A module containing the "Server" class.
The server class implements server socket initialization, client acceptance logic, and the creation of new
communication channels.
"""
import socket
import logging
from p2p_fileshare.server.channel import ClientChannel
from p2p_fileshare.server.db_manager import DBManager
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.server import Server


logger = logging.getLogger(__file__)


class MetadataServer(Server):
    """
    This class takes care of the server's core logic - accepting new clients and starting an appropriate ClientChannel
    for them.
    """
    def __init__(self, port=0, db_path=None):
        super().__init__(port)
        self._db = DBManager(db_path)

    def _receive_new_client(self, client: socket.socket, client_address: tuple[str, int], finished_socket: socket.socket):
        new_channel = Channel(client)
        return ClientChannel(new_channel, self._db, self.get_all_clients_info, finished_socket)

    def _remove_old_clients(self):
        """
        Removes invalid communication channels from the list.
        """
        remove_list = []
        for communication_channel in self._communication_channels:
            if not communication_channel.is_active:
                remove_list.append(communication_channel)
        for item in remove_list:
            logger.debug(f"Removing inactive channel with client {item.get_client_connection_info()[0]}")
            self._communication_channels.remove(item)

    def get_all_clients_info(self):
        return [channel.get_client_connection_info() for channel in self._items]
