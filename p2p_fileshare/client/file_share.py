"""
This module contains the local file sharing server which allows different clients to access this client directly in a
p2p fashion and start a file transfer.
"""
from p2p_fileshare.framework.server import Server
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.types import FileObject
from p2p_fileshare.framework.messages import StartFileTransferMessage, ChunkDataResponseMessage
from db_manager import DBManager
from logging import getLogger
from threading import Thread
import socket


logger = getLogger(__file__)


# NOTE: if we want to be able to query ongoing file transfers, this should probably be refactored into a class.
def transfer_file_to_client(downloader_socket: socket.socket, db_manager: DBManager):
    channel = Channel(downloader_socket)
    transfer_request = channel.wait_for_message(StartFileTransferMessage)
    file_path = db_manager.get_shared_file_path(transfer_request._file_id)
    if file_path is None:
        logger.warning(f"A client has requested a file which this client does not share. ID: {unique_id}")
        return  # maybe raise?
    file_object = FileObject(file_path)
    chunk_data = file_object.read_chunk(transfer_request._chunk_num)
    channel.send_message(ChunkDataResponseMessage(transfer_request._file_id, transfer_request._chunk_num, chunk_data))
    # TODO: we now have the file path and the channel to the client. Wait for the client to request chunks of the file
    # and transfer them to it via channel.send_message(...)


class FileShareChannel(object):
    def __init__(self, downloader_socket):
        self._channel = Channel(downloader_socket)


class FileShareServer(Server):
    """
    The server responsible for managing file sharing.
    New clients that wish to download files we're currently sharing will connect to this server's socket, and in return
    we will start a new transfer channel for them which will pass chunks of the file according to their requests.
    """
    def __init__(self, local_db: DBManager, port=0):
        super().__init__(port)
        self._active_transfers = []
        self._db = local_db

    def _receive_new_client(self, client: socket.socket, client_address: tuple[str, int]):
        new_transfer_thread = Thread(target=transfer_file_to_client, args=(client, self._db))
        self._active_transfers.append(new_transfer_thread)
        new_transfer_thread.start()

    def _remove_old_clients(self):
        pass  # TODO: implement

    @property
    def sharing_port(self):
        return self._socket.getsockname()[1]