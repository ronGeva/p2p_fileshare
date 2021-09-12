"""
A module governing file access.
"""
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import SearchFileMessage


class FilesManager(object):
    def __init__(self, communication_channel: Channel):
        self._communication_channel = communication_channel

    def search_file(self, file_name: str):
        """
        :param file_name: The name (or a substring) of a the file name
        :return: A list of SharedFile objects
        """
        msg = SearchFileMessage(file_name)
        self._communication_channel.send_message(msg)
        # TODO: get response and return it

    def share_file(self, unique_id: str):
        raise NotImplementedError

    def download_file(self, unique_id: str):
        raise NotImplementedError
