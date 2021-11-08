"""
A module governing file access.
"""
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import SearchFileMessage, FileListMessage, ShareFileMessage, \
    SharingInfoRequestMessage, SharingInfoResponseMessage
from p2p_fileshare.framework.types import SharedFile
from file_share import FileShareServer
from db_manager import DBManager
from threading import Thread
import os
import hashlib


class FilesManager(object):
    def __init__(self, communication_channel: Channel):
        self._communication_channel = communication_channel
        self._local_db = DBManager()
        self._file_share_server = None
        self._file_share_thread = None
        self.__initialize_file_share_server()

    def __start_file_share(self):
        # TODO: pass the sharing port to the server. Right now after stopping the app and starting it back on again
        # the server won't know our sharing port until we share a new file
        self._file_share_server = FileShareServer(self._local_db)
        self._file_share_thread = Thread(target=self._file_share_server.main_loop)
        self._file_share_thread.start()

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

        shared_file_message = ShareFileMessage(shared_file, self._file_share_server.sharing_port)
        self._communication_channel.send_message(shared_file_message)


    def download_file(self, unique_id: str, local_path: str):
        sharing_info_request = SharingInfoRequestMessage(unique_id)
        self._communication_channel.send_message(sharing_info_request)
        shared_file_info = self._communication_channel.wait_for_message(SharingInfoResponseMessage).shared_file
        # TODO: we now have all the information needed to initialize the file download. Implement the file download
        pass
