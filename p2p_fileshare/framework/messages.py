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

GENERAL_SUCESS_MESSAGE_TYPE = 0
GENERAL_ERROR_MESSAGE_TYPE = 999
SEARCH_FILE_MESSAGE_TYPE = 1
FILE_LIST_MESSAGE_TYPE = 2
FILE_MESSAGE_TYPE = 3
SHARE_FILE_MESSAGE_TYPE = 4
CLIENT_ID_MESSAGE_TYPE = 5
SHARING_INFO_REQUEST_MESSAGE_TYPE = 6
SHARING_INFO_RESPONSE_MESSAGE_TYPE = 7
START_FILE_TRANSFER_MESSAGE_TYPE = 8
CHUNK_DATA_RESPONSE_MESSAGE_TYPE = 9
SUCCESSFUL_CHUNK_DOWNLOAD_MESSAGE_TYPE = 10
UNSUCCESSFUL_CHUNK_DOWNLOAD_MESSAGE_TYPE = 11


class MessageType(enum.Enum):
    pass


class Message(object):
    message_types = {SEARCH_FILE_MESSAGE_TYPE: SearchFileMessage,
                     FILE_LIST_MESSAGE_TYPE: FileListMessage,
                     SHARE_FILE_MESSAGE_TYPE: ShareFileMessage,
                     CLIENT_ID_MESSAGE_TYPE: ClientIdMessage,
                     SHARING_INFO_REQUEST_MESSAGE_TYPE: SharingInfoRequestMessage,
                     SHARING_INFO_RESPONSE_MESSAGE_TYPE: SharingInfoResponseMessage,
                     START_FILE_TRANSFER_MESSAGE_TYPE: StartFileTransferMessage
                     CHUNK_DATA_RESPONSE_MESSAGE_TYPE: ChunkDataResponseMessage}

    def serialize(self):
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data):
        msg_type = unpack("I", data[:4])[0]
        if msg_type in message_types:
            return message_types[msg_type].deserialize(data)
        raise RuntimeError(f"Failed to deserialize message! Got type: {msg_type}")

    @property
    def matching_response_type(self):
        raise NotImplementedError

    @property
    def type(self):
        raise NotImplementedError


class GeneralSuccessMessage(Message):
    def __init__(self, success_info: str):
        self.success_info = success_info

    @classmethod
    def deserialize(cls, data):
        return GeneralSuccessMessage(data[4:].decode('utf-8'))

    def serialize(self):
        return struct.pack("I", self.type()) + bytes(self.success_info, "utf-8")

    @property
    def type(self):
        return GENERAL_SUCESS_MESSAGE_TYPE

class GeneralErrorMessage(Message):
    def __init__(self, error_info: str):
        self.error_info = error_info

    @classmethod
    def deserialize(cls, data):
        return GeneralErrorMessage(data[4:].decode('utf-8'))

    def serialize(self):
        return struct.pack("I", self.type()) + bytes(self.error_info, "utf-8")

    @property
    def type(self):
        return GENERAL_ERROR_MESSAGE_TYPE


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
        return FILE_MESSAGE_TYPE


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
        return FILE_LIST_MESSAGE_TYPE

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
        return SEARCH_FILE_MESSAGE_TYPE

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
        return SHARE_FILE_MESSAGE_TYPE


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
        return CLIENT_ID_MESSAGE_TYPE


class FileDownloadRequest(Message):
    """
    This message represents all messages including only the unique id of the file.
    Messages which only need to transfer this data can inherit from this class and only implement the type method.
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


class SharingInfoRequestMessage(FileDownloadRequest):
    """
    This message is used by the client to retrieve information about clients that share a specific file.
    It is used by clients to initialize file download.
    """
    @classmethod
    def type(cls):
        return SHARING_INFO_REQUEST_MESSAGE_TYPE


class StartFileTransferMessage(FileDownloadRequest):
    """
    This message is used by the client to let another client (the sharing client) know what file he'd like to download.
    """
    def __init__(self, file_id: str, chunk_num: int):
        self._file_id = file_id
        self._chunk_num = chunk_num

    @classmethod
    def deserialize(cls, data: bytes):
        file_id = data[4: 4 + UNIQUE_ID_LENGTH].decode("utf-8")
        chunk_num = unpack("I", data[4 + UNIQUE_ID_LENGTH: 8 + UNIQUE_ID_LENGTH])[0]
        return StartFileTransferMessage(file_id=file_id, chunk_num=chunk_num)

    def serialize(self):
        file_id_data = self._file_id.encode("utf-8")
        chunk_num = pack("I", self._chunk_num)
        return pack("I", self.type()) + file_id_data + chunk_num

    @classmethod
    def type(cls):
        return START_FILE_TRANSFER_MESSAGE_TYPE

    @property
    def matching_response_type(self):
        return ChunkDownloadDataResponse


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
        return SHARING_INFO_RESPONSE_MESSAGE_TYPE


class ChunkDataResponseMessage(FileDownloadRequest):
    """
    This message is used by the client to let another client (the sharing client) know what file he'd like to download.
    """
    def __init__(self, file_id: str, chunk_num: int, data: str):
        self._file_id = file_id
        self._chunk_num = chunk_num
        self.data = data

    @classmethod
    def deserialize(cls, data: bytes):
        file_id = data[4: 4 + UNIQUE_ID_LENGTH].decode("utf-8")
        chunk_num = unpack("I", data[4 + UNIQUE_ID_LENGTH: 8 + UNIQUE_ID_LENGTH])[0]
        chunk_data = data[4 + UNIQUE_ID_LENGTH:]
        assert len(chunk_data) == DownloadedFileObject.CHUNK_SIZE
        return ChunkDownloadDataResponse(file_id=file_id, chunk_num=chunk_num, data=chunk_data)

    def serialize(self):
        file_id_data = self._file_id.encode("utf-8")
        chunk_num = pack("I", self._chunk_num)
        assert len(chunk_data) == DownloadedFileObject.CHUNK_SIZE
        return pack("I", self.type()) + file_id_data + chunk_num + self.data

    @classmethod
    def type(cls):
        return CHUNK_DATA_RESPONSE_MESSAGE_TYPE


class ChunkDownloadUpdateMessage(Message):
    def __init__(self, file_id: str, chunk_num: int, origin_client_id: str):
        self._file_id = file_id
        self._chunk_num = chunk_num
        self._origin_client_id = origin_client_id

    @classmethod
    def deserialize(cls, data: bytes):
        file_id = data[4: 4 + UNIQUE_ID_LENGTH].decode("utf-8")
        chunk_num = unpack("I", data[4 + UNIQUE_ID_LENGTH: 8 + UNIQUE_ID_LENGTH])[0]
        origin_client_id = data[8 + UNIQUE_ID_LENGTH: 8 + UNIQUE_ID_LENGTH + UNIQUE_ID_LENGTH].decode("utf-8")
        return SharingInfoRequestMessage(file_id=file_id, chunk_num=chunk_num, origin_client_id=origin_client_id)

    def serialize(self):
        file_id = self._file_id.encode("utf-8")
        chunk_num = pack("I", self._chunk_num)
        origin_client_id = self._origin_client_id.encode("utf-8")
        return pack("I", self.type()) + file_id + chunk_num + origin_client_id


class SuccessfuleChunkDownloadUpdateMessage(ChunkDownloadUpdateMessage):
    @classmethod
    def type(cls):
        return SUCCESSFUL_CHUNK_DOWNLOAD_MESSAGE_TYPE


class UnsuccessfuleChunkDownloadUpdateMessage(ChunkDownloadUpdateMessage):
    def type(cls):
        return UNSUCCESSFUL_CHUNK_DOWNLOAD_MESSAGE_TYPE
