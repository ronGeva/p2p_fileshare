"""
A module containing the communication channel logic.
Each communication channel represents a single channel between the server and a client.
All actions in the channel must be made in a thread-safe way to ensure no data corruption is taking place.
"""
from threading import Thread
from select import select
from logging import getLogger
from db_manager import DBManager
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import Message, SearchFileMessage, FileListMessage, ShareFileMessage, \
    ClientIdMessage, SharingInfoRequestMessage, SharingInfoResponseMessage, GeneralSuccessMessage, GeneralErrorMessage
from p2p_fileshare.framework.types import SharingClientInfo, SharedFileInfo
from typing import Callable
import time
import hashlib


logger = getLogger(__file__)


class ClientChannel(object):
    def __init__(self, client_channel: Channel, db: DBManager, get_all_clients_func: Callable):
        self._channel = client_channel
        self._db = db
        self._closed = False # TODO: check if needed
        self._client_id = None
        self._thread = Thread(target=self.__start)
        self._thread.start()
        self._get_all_clients_func = get_all_clients_func
        self._client_share_port = None

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        while not self._channel._is_socket_closed:
            rlist, _, _ = select([self._channel], [], [], 0)
            if rlist:
                msg = self._channel.recv_message()  # TODO: make sure an entire message was received
                # TODO: perform actions with the command
                logger.debug(f"received message: {msg}")
                response = self._do_action(msg)
                if response is not None:
                    self._channel.send_message(response)

    def _do_action(self, msg: Message):
        """
        Perform an action according to the incoming message and returns an appropriate response message.
        :param msg: The message received.
        :return:
        """
        if isinstance(msg, SearchFileMessage):
            matching_files = self._db.search_file(msg.name)
            return FileListMessage(matching_files)
        if isinstance(msg, ShareFileMessage):
            self._client_share_port = msg.share_port
            if self._db.new_share(msg.file, self._client_id):
                return GeneralSuccessMessage('File shared successfully!')
            return GeneralErrorMessage('File is already shared!')
        if isinstance(msg, ClientIdMessage):
            unique_id = msg.unique_id
            logger.debug(f"new client unique id is {unique_id}")
            if unique_id == msg.NO_ID_MAGIC:
                unique_id = hashlib.md5(bytes(str(time.time()), 'utf-8')).hexdigest()  # TODO: implement this better
                self._db.add_new_client(unique_id)
                self._client_id = unique_id
                return ClientIdMessage(unique_id)
            else:
                self._db.add_new_client(unique_id)
                self._client_id = unique_id
        if isinstance(msg, SharingInfoRequestMessage):
            shared_file = self._db.get_shared_file_info(msg.file_unique_id)
            sharing_clients = self._db.find_sharing_clients(msg.file_unique_id)
            current_clients = self._get_all_clients_func()

            # filter out current clients which do not share the file
            connected_sharing_clients = [SharingClientInfo(current_client[0], (current_client[1], current_client[2])) for current_client in current_clients
                                              if current_client[0] in sharing_clients]
            shared_file.origins = connected_sharing_clients
            #shared_file_info = SharedFileInfo(msg.file_unique_id, connected_sharing_clients)
            return SharingInfoResponseMessage(shared_file)

        return None

    def __stop(self):
        """
        Stops the channel's thread and signal the main Server component that this channel is invalid.
        """
        raise NotImplementedError

    def get_client_connection_info(self):
        """
        Returns a 3 tuple containing the client id, its current IP address, and the port in which other clients can
        contact it in order to initialize file downloads.
        """
        return self._client_id, self._channel.getpeername()[0], self._client_share_port

    @property
    def is_active(self):
        return self._thread.is_alive()