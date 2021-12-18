"""
A module governing file access.
"""
import logging

from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import SearchFileMessage, FileListMessage, ShareFileMessage, \
    SharingInfoRequestMessage, SharingInfoResponseMessage, RemoveShareMessage, SharePortMessage
from p2p_fileshare.framework.types import SharedFile
from p2p_fileshare.client.file_share import FileShareServer
from p2p_fileshare.client.db_manager import DBManager
from p2p_fileshare.client.file_transfer import FileDownloader
from threading import Thread
from typing import Optional
import os
import hashlib


logger = logging.getLogger(__name__)


class FilesManager(object):
    def __init__(self, communication_channel: Channel, username: Optional[str]):
        self._communication_channel = communication_channel
        self._local_db = DBManager(self.generate_db_path(username))
        self._file_share_server = None  # type: Optional[FileShareServer]
        self._file_share_thread = None
        self.__initialize_file_share_server()
        self.downloaders = []

    def __del__(self):
        if self._file_share_server is not None:
            self._file_share_server.stop()

    @staticmethod
    def generate_db_path(username: str) -> str:
        return "{}.db".format(username)

    def __start_file_share(self):
        self._file_share_server = FileShareServer(local_db=self._local_db)
        self._file_share_thread = Thread(target=self._file_share_server.main_loop)
        self._file_share_thread.start()
        # let the server know our share port so that other clients can communicate with us
        self._communication_channel.send_message(SharePortMessage(self._file_share_server.sharing_port))

    def __initialize_file_share_server(self):
        if self._local_db.is_there_any_shared_file():
            self.__start_file_share()

    @staticmethod
    def _calculate_file_hash(file_path: str) -> str:
        """
        Calculates the hash of a local file's data by reading chunks of it and feeding them to the md5 algorithm.
        :return an hexadecimal representation of the file's hash.
        """
        current_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            file_chunk = f.read(1024 * 1024)
            while len(file_chunk) > 0:
                current_md5.update(file_chunk)
                file_chunk = f.read(1024 * 1024)
        return current_md5.hexdigest()

    def search_file(self, file_name: str) -> list[SharedFile]:
        """
        :param file_name: The name (or a substring) of a the file name
        :return: A list of SharedFile objects
        """
        msg = SearchFileMessage(file_name)
        self._communication_channel.send_message(msg)
        return self._communication_channel.wait_for_message(FileListMessage).files

    def share_file(self, file_path: str):
        """
        Starts to share a single file by notifying the server of the action and initializing the file sharing server.
        :param file_path: The local path of the file to share.
        :return: None
        """
        file_stats = os.stat(file_path)
        file_hash = self._calculate_file_hash(file_path)
        shared_file = SharedFile(file_hash, os.path.basename(file_path), int(file_stats.st_mtime), file_stats.st_size,
                                 [])

        self._local_db.add_share(file_hash, file_path)
        if self._file_share_server is None:
            self.__start_file_share()

        shared_file_message = ShareFileMessage(shared_file)
        self._communication_channel.send_message(shared_file_message)

    def download_file(self, unique_id: str, local_path: str):
        if unique_id+local_path in self.downloaders:
            logger.warning('Given file was already downloaded to given location, please list and remove it first')
        else:
            logger.debug("Sending file info request to server")
            sharing_info_request = SharingInfoRequestMessage(unique_id)
            self._communication_channel.send_message(sharing_info_request)
            shared_file = self._communication_channel.wait_for_message(SharingInfoResponseMessage).shared_file
            for sc in shared_file.origins:
                logger.debug(f"Origin: {sc.ip}:{sc.port}")

            file_downloader = FileDownloader(shared_file, self._communication_channel, local_path)
            self.downloaders.append(file_downloader)
            logger.debug('FileDownloader started!')

    def list_downloads(self) -> list[FileDownloader]:
        return self.downloaders

    def remove_download(self, downloader_id: int):
        if not (0 <= downloader_id < len(self.downloaders)):
            logger.warning('Unknown downloader')
        else:
            fd = self.downloaders.pop(downloader_id)
            fd.stop()

    def list_shares(self):
        return self._local_db.list_shares()

    def remove_share(self, unique_id: str):
        self._communication_channel.send_message(RemoveShareMessage(unique_id))
        self._local_db.remove_share(unique_id)
