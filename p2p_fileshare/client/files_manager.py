"""
A module governing file access.
"""
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import SearchFileMessage, FileListMessage, SharedFileMessage
from p2p_fileshare.framework.types import SharedFile, calculate_file_hash, FileObject
import os
import hashlib
from threading import Lock

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
        """
        Starts to share a single file by notifying the server of the action and initializing the file sharing server.
        :param file_path: The local path of the file to share.
        :return: None
        """
        new_file = FileObject(file_path)
        shared_file = new_file.get_shared_file()
        shared_file_message = SharedFileMessage(shared_file)
        self._communication_channel.send_message(shared_file_message)
        # TODO: implement file sharing server - from now on this client should allow other clients to download this file

    def download_file(self, unique_id: str):
        raise NotImplementedError
