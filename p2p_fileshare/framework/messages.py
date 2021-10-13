"""
A module containing Client - Server messages.
TODO: Change all magic types into some form of an enum for better readability
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
        known_message_types = [SearchFileMessage, FileListMessage, SharedFileMessage, ClientIdMessage]
        msg_type = unpack("I", data[:4])[0]
        for known_message_type in known_message_types:
            if msg_type == known_message_type.type():
                return known_message_type.deserialize(data)
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
        unique_id = data[12 + name_len: 44 + name_len].decode('utf-8')  # unique id is 32 bytes long
        next_msg_offset = 44 + name_len  # TODO: Refactor this to be better - maybe use protobuf?
        return FileMessage(SharedFile(unique_id, name, modification_time, size, [])), next_msg_offset

    def serialize(self):
        # TODO: serialize origins, unique id
        data = struct.pack("I", len(self.file.name)) + self.file.name.encode("utf-8") + \
               struct.pack("II", self.file.modification_time, self.file.size) + bytes(self.file.unique_id, 'utf-8')
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


class SharedFileMessage(Message):
    def __init__(self, shared_file: SharedFile):
        self.file = shared_file

    @classmethod
    def deserialize(cls, data):
        file_message, _ = FileMessage.deserialize(data[4:])
        shared_file = file_message.file
        return SharedFileMessage(shared_file)

    def serialize(self):
        file_message = FileMessage(self.file)
        return pack("I", self.type()) + file_message.serialize()

    @classmethod
    def type(cls):
        return 3


class ClientIdMessage(Message):
    """
    This message is used by the server to identify the client of its unique ID, to be used in all connections from now
    on.
    """
    UNIQUE_ID_LENGTH = 32
    NO_ID_MAGIC = 'ff' * 16

    def __init__(self, unique_id: str):
        self.unique_id = unique_id or self.NO_ID_MAGIC

    @classmethod
    def deserialize(cls, data: bytes):
        unique_id = data[4: 4 + cls.UNIQUE_ID_LENGTH].decode("utf-8")
        return ClientIdMessage(unique_id)

    def serialize(self):
        unique_id_data = self.unique_id.encode("utf-8")
        return pack("I", self.type()) + unique_id_data

    @classmethod
    def type(cls):
        return 4
