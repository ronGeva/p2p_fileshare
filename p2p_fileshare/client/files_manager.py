"""
A module governing file access.
"""
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import SearchFileMessage, FileListMessage, SharedFileMessage
from p2p_fileshare.framework.types import SharedFile
import os
import hashlib


class FilesManager(object):
    def __init__(self, communication_channel: Channel):
        self._communication_channel = communication_channel

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
        return self._communication_channel.wait_for_response(FileListMessage).files
        # TODO: get response and return it

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
        shared_file_message = SharedFileMessage(shared_file)
        self._communication_channel.send_message(shared_file_message)
        # TODO: implement file sharing server - from now on this client should allow other clients to download this file

    def download_file(self, unique_id: str):
        raise NotImplementedError
