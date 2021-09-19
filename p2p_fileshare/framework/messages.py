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
            return SearchFileMessage.deserialize(data)
        elif msg_type == FileListMessage.type():
            return FileListMessage.deserialize(data)
        raise RuntimeError("Failed to deserialize message! Got type: {}".format(msg_type))

    @property
    def matching_response_type(self):
        raise NotImplementedError

    @property
    def type(self):
        raise NotImplementedError


class FileMessage(Message):
    def __init__(self, file: SharedFile):
        self.file = file

    @classmethod
    def deserialize(cls, data):
        # TODO: desrialize origins, unique id
        name_len = struct.unpack("I", data[:4])[0]
        name = data[4:4 + name_len].decode("utf-8")
        modification_time, size = struct.unpack("II", data[4 + name_len:12 + name_len])
        next_msg_offset = 12 + name_len  # TODO: Refactor this to be better - maybe use protobuf?
        return FileMessage(SharedFile("", name, modification_time, size, [])), 12 + name_len

    def serialize(self):
        # TODO: serialize origins, unique id
        data = struct.pack("I", len(self.file.name)) + self.file.name.encode("utf-8") + \
               struct.pack("II", self.file.modification_time, self.file.size)
        return data

    @property
    def type(self):
        return 2


class FileListMessage(Message):
    def __init__(self, files: list[SharedFile]):
        self.files = files

    @classmethod
    def deserialize(cls, data):
        amount_of_files = struct.unpack("I", data[4:8])[0]
        files = []
        data_index = 8
        for i in range(amount_of_files):
            file_msg, file_len = FileMessage.deserialize(data[data_index:])
            files.append(file_msg.file)
            data_index += file_len
        return FileListMessage(files)

    def serialize(self):
        msg_type_data = struct.pack("I", self.type())
        amount_of_files = struct.pack("I", len(self.files))
        files_data = bytes()
        for file in self.files:
            files_data += FileMessage(file).serialize()
        return msg_type_data + amount_of_files + files_data

    @classmethod
    def type(cls):
        return 1

    @property
    def matching_response_type(self):
        return None


class SearchFileMessage(Message):
    def __init__(self, name: str):
        self.name = name

    @classmethod
    def deserialize(cls, data):
        return SearchFileMessage(data[4:].decode('utf-8'))

    def serialize(self):
        return struct.pack("I", self.type()) + bytes(self.name, "utf-8")

    @classmethod
    def type(cls):
        return 0

    @property
    def matching_response_type(self):
        return FileListMessage
