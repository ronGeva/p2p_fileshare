"""
This module contains the local file sharing server which allows different clients to access this client directly in a
p2p fashion and start a file transfer.
"""
from p2p_fileshare.framework.server import Server
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.types import FileObject
from p2p_fileshare.framework.messages import StartFileTransferMessage, ChunkDataResponseMessage, RTTCheckMessage, RTTResponseMessage
from p2p_fileshare.framework.selectable_event import signal
from p2p_fileshare.client.db_manager import DBManager
from logging import getLogger
from threading import Thread
import socket


logger = getLogger(__file__)


def transfer_file_chunk_to_client(downloader_socket: socket.socket, db_manager: DBManager,
                                  finished_socket: socket.socket):
    """
    Waits for the remote client to request a single file chunk, and transfers it to him via the
    ChunkDataResponseMessage.
    At the end of this function the finished_socket is signaled to let the FileShareServer know the thread has finished.
    """
    channel = Channel(downloader_socket)
    client_request = channel.wait_for_messages([StartFileTransferMessage, RTTCheckMessage])
    if isinstance(client_request, RTTCheckMessage):
        logger.debug("Got a RTT check message")
        channel.send_message(RTTResponseMessage(client_request.send_time))
    else:
        file_path = db_manager.get_shared_file_path(client_request._file_id)
        if file_path is None:
            logger.warning(f"A client has requested a file which this client does not share. ID: {unique_id}")
            return  # maybe raise?
        file_object = FileObject(file_path, is_local=True)
        chunk_data = file_object.read_chunk(client_request._chunk_num)
        logger.debug("Sending a ChunkDataResponseMessage to another client")
        channel.send_message(ChunkDataResponseMessage(client_request._file_id, client_request._chunk_num, chunk_data))
    signal(finished_socket)
    channel.close()


class FileShareServer(Server):
    """
    The server responsible for managing file sharing.
    New clients that wish to download files we're currently sharing will connect to this server's socket, and in return
    we will start a new transfer channel for them which will pass chunks of the file according to their requests.
    """
    def __init__(self, local_db: DBManager, port=0):
        super().__init__(port)
        self._db = local_db

    def _receive_new_client(self, client: socket.socket, client_address: tuple[str, int], finished_socket: socket.socket):
        new_transfer_thread = Thread(target=transfer_file_chunk_to_client, args=(client, self._db, finished_socket))
        new_transfer_thread.start()
        return new_transfer_thread

    def _remove_old_clients(self):
        """
        Filters out all finished threads from the list of running threads.
        """
        self._active_transfers = [active_transfer for active_transfer in self._active_transfers
                                  if active_transfer.is_alive()]

    @property
    def sharing_port(self):
        return self._socket.getsockname()[1]