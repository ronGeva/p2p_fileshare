"""
A module governing file access.
"""
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import SearchFileMessage, FileListMessage, SharedFileMessage
from p2p_fileshare.framework.types import SharedFile
import os


class FilesManager(object):
    def __init__(self, communication_channel: Channel):
        self._communication_channel = communication_channel

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
        file_stats = os.stat(file_path)
        # TODO: what about unique ID during file share? The client cannot determine the unique id...
        shared_file = SharedFile("", os.path.basename(file_path), int(file_stats.st_mtime), file_stats.st_size, [])
        shared_file_message = SharedFileMessage(shared_file)
        self._communication_channel.send_message(shared_file_message)

    def download_file(self, unique_id: str):
        raise NotImplementedError
