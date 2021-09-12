"""
A module containing Client - Server messages.
"""
import enum
import struct
from struct import pack, unpack
from p2p_fileshare.framework.types import SharedFile


class MessageType(enum.Enum):
    pass


class Message(object):
    def serialize(self):
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data):
        msg_type = unpack("I", data[:4])[0]
        if msg_type == SearchFileMessage.type():
            return SearchFileMessage(data[4:])
        raise RuntimeError("Failed to deserialize message!")

    @property
    def matching_response_type(self):
        raise NotImplementedError

    @property
    def type(self):
        raise NotImplementedError


class FileListMessage(Message):
    def __init__(self, files: list[SharedFile]):
        self.files = files


class SearchFileMessage(Message):
    def __init__(self, name):
        self.name = name

    def serialize(self):
        return struct.pack("I", self.type()) + bytes(self.name, "utf-8")

    @classmethod
    def type(cls):
        return 0

    @property
    def matching_response_type(self):
        return FileListMessage
