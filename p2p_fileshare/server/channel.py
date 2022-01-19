"""
A module containing the communication channel logic.
Each communication channel represents a single channel between the server and a client.
All actions in the channel must be made in a thread-safe way to ensure no data corruption is taking place.
"""
from threading import Thread
from select import select
from logging import getLogger
from p2p_fileshare.server.db_manager import DBManager
from p2p_fileshare.framework.channel import Channel, SocketClosedException
from p2p_fileshare.framework.messages import Message, SearchFileMessage, FileListMessage, ShareFileMessage, \
    ClientIdMessage, SharingInfoRequestMessage, SharingInfoResponseMessage, GeneralSuccessMessage, GeneralErrorMessage, \
    RemoveShareMessage, SharePortMessage
from p2p_fileshare.framework.types import SharingClientInfo
from p2p_fileshare.framework.selectable_event import signal
from typing import Callable
import time
import hashlib
import socket


logger = getLogger(__file__)


class ClientChannel(object):
    """
    A class governing the interactions with a single client from the perspective of the metadata server.
    """
    def __init__(self, client_channel: Channel, db: DBManager, get_all_clients_func: Callable,
                 finished_socket: socket.socket):
        self._channel = client_channel
        self._db = db
        self._client_id = None
        self._thread = Thread(target=self.__start)
        self._thread.start()
        self._get_all_clients_func = get_all_clients_func
        self._client_share_port = None
        self._finished_socket = finished_socket

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        The server's clientChannel waits infinitely for new messages to be received.
        For each new message it performs the action requested by the user.
        """
        try:
            while True:
                # infinite wait - once the channel is closed the select will be triggered, once we'll attempt to read
                # an exception will be thrown forcing us to exit.
                rlist, _, _ = select([self._channel], [], [])
                if rlist:
                    try:
                        msg = self._channel.recv_message()
                    except SocketClosedException as e:
                        logger.debug('Socket closed')
                        break
                    logger.debug(f"received message: {msg}")
                    response = self._do_action(msg)
                    if response is not None:
                        self._channel.send_message(response)
        finally:
            signal(self._finished_socket)

    def __get_connected_sharing_clients(self, file_unique_id: str) -> list[SharingClientInfo]:
        """
        Retrieves all the clients that both share the file and are currently connected.
        :param file_unique_id: The unique ID of the file.
        :return: A list of ClientChannel objects.
        """
        sharing_clients = self._db.find_sharing_clients(file_unique_id)
        current_clients = self._get_all_clients_func()

        # filter out current clients which do not share the file
        return [SharingClientInfo(current_client[0], (current_client[1], current_client[2]))
                for current_client in current_clients if
                current_client[0] in sharing_clients and current_client[1] is not None]

    def _do_action(self, msg: Message):
        """
        Perform an action according to the incoming message and returns an appropriate response message.
        :param msg: The message received.
        :return:
        """
        if isinstance(msg, SearchFileMessage):
            matching_files = self._db.search_file(msg.name)
            matching_files = [matching_file for matching_file in matching_files
                              if self.__get_connected_sharing_clients(matching_file.unique_id)]
            return FileListMessage(matching_files)
        if isinstance(msg, SharePortMessage):
            self._client_share_port = msg.share_port
        if isinstance(msg, ShareFileMessage):
            if self._db.new_share(msg.file, self._client_id):
                return GeneralSuccessMessage('File shared successfully!')
            return GeneralErrorMessage('File is already shared!')
        if isinstance(msg, ClientIdMessage):
            unique_id = msg.unique_id
            logger.debug(f"new client unique id is {unique_id}")
            if unique_id == msg.NO_ID_MAGIC:
                unique_id = hashlib.md5(bytes(str(time.time()), 'utf-8')).hexdigest()
                self._db.add_new_client(unique_id)
                self._client_id = unique_id
                return ClientIdMessage(unique_id)
            else:
                self._db.add_new_client(unique_id)
                self._client_id = unique_id
        if isinstance(msg, SharingInfoRequestMessage):
            shared_file = self._db.get_shared_file_info(msg.file_unique_id)
            if shared_file is None:
                return GeneralErrorMessage('Found no files with the unique ID specified!')

            connected_sharing_clients = self.__get_connected_sharing_clients(msg.file_unique_id)
            shared_file.origins = connected_sharing_clients
            return SharingInfoResponseMessage(shared_file)
        if isinstance(msg, RemoveShareMessage):
            if self._db.remove_share(msg.unique_id, self._client_id):
                return GeneralSuccessMessage('Share was deleted successfully!')
            else:
                return GeneralErrorMessage('Failed to delete share: No such share was found!')

        return None

    def get_client_connection_info(self):
        """
        Returns a 3 tuple containing the client id, its current IP address, and the port in which other clients can
        contact it in order to initialize file downloads.
        """
        return self._client_id, self._channel.getpeername()[0], self._client_share_port

    @property
    def is_active(self):
        return self._thread.is_alive()
