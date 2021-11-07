"""
A module containing Client - Server messages.
TODO: Change all magic types into some form of an enum for better readability
"""
import enum
import struct
from struct import pack, unpack
from socket import inet_aton, inet_ntoa
from p2p_fileshare.framework.types import SharedFile, SharingClientInfo, SharedFileInfo

UNIQUE_ID_LENGTH = 32

class MessageType(enum.Enum):
    pass


class Message(object):
    def serialize(self):
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data):
        known_message_types = [SearchFileMessage, FileListMessage, ShareFileMessage, ClientIdMessage,
                               SharingInfoResponseMessage, SharingInfoRequestMessage]
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


class ShareFileMessage(Message):
    def __init__(self, shared_file: SharedFile, share_port: int):
        self.file = shared_file
        self.share_port = share_port

    @classmethod
    def deserialize(cls, data):
        file_message, file_msg_len = FileMessage.deserialize(data[4:])
        shared_file = file_message.file
        port = unpack("H", data[4 + file_msg_len: 6 + file_msg_len])[0]
        return ShareFileMessage(shared_file, port)

    def serialize(self):
        file_message = FileMessage(self.file)
        return pack("I", self.type()) + file_message.serialize() + pack("H", self.share_port)

    @classmethod
    def type(cls):
        return 3


class ClientIdMessage(Message):
    """
    This message is used by the server to identify the client of its unique ID, to be used in all connections from now
    on.
    """
    NO_ID_MAGIC = 'ff' * 16

    def __init__(self, unique_id: str):
        self.unique_id = unique_id or self.NO_ID_MAGIC

    @classmethod
    def deserialize(cls, data: bytes):
        unique_id = data[4: 4 + UNIQUE_ID_LENGTH].decode("utf-8")
        return ClientIdMessage(unique_id)

    def serialize(self):
        unique_id_data = self.unique_id.encode("utf-8")
        return pack("I", self.type()) + unique_id_data

    @classmethod
    def type(cls):
        return 4


class SharingInfoRequestMessage(Message):
    """
    This message is used by the client to retrieve information about clients that share a specific file.
    It is used by clients to initialize file download.
    """
    def __init__(self, file_unique_id: str):
        self.file_unique_id = file_unique_id

    @classmethod
    def deserialize(cls, data: bytes):
        unique_id = data[4: 4 + UNIQUE_ID_LENGTH].decode("utf-8")
        return SharingInfoRequestMessage(unique_id)

    def serialize(self):
        unique_id_data = self.file_unique_id.encode("utf-8")
        return pack("I", self.type()) + unique_id_data

    @classmethod
    def type(cls):
        return 5


class SharingInfoResponseMessage(Message):
    """
    A response to SharingInfoRequestMessage, containing information about all the clients that share a specific file.
    NOTE: This message serializes a non-existing port to 0 and deserialize the sharing port 0 as a non-existent sharing
    port.
    """
    def __init__(self, shared_file: SharedFileInfo):
        self.shared_file = shared_file

    @classmethod
    def deserialize(cls, data: bytes):
        unique_id = data[4: 4 + UNIQUE_ID_LENGTH].decode("utf-8")
        amount_of_sharing_clients = unpack("I", data[4 + UNIQUE_ID_LENGTH: 8 + UNIQUE_ID_LENGTH])[0]
        sharing_clients = []
        index = 8 + UNIQUE_ID_LENGTH
        for _ in range(amount_of_sharing_clients):
            ip = inet_ntoa(data[index: index + 4])
            port = unpack("H", data[index + 4: index + 6])[0]
            if port == 0:
                port = None
            sharing_clients.append(SharingClientInfo((ip, port)))
            index += 6
        return SharingInfoResponseMessage(SharedFileInfo(unique_id, sharing_clients))

    def serialize(self):
        amount_of_sharing_clients_data = pack("I", len(self.shared_file.sharing_clients))
        unique_id_data = self.shared_file.unique_id.encode("utf-8")
        sharing_clients_data = bytes()
        for sharing_client in self.shared_file.sharing_clients:
            sharing_clients_data += inet_aton(sharing_client.ip)
            port = sharing_client.port if sharing_client.port is not None else 0
            sharing_clients_data += pack("H", port)
        return pack("I", self.type()) + unique_id_data + amount_of_sharing_clients_data + sharing_clients_data

    @classmethod
    def type(cls):
        return 6
