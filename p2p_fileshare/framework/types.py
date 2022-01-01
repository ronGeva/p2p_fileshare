"""
A module containing different types used by the application
"""
from typing import Optional
from math import ceil
import os
import hashlib
import logging

logger = logging.getLogger(__name__)

class FileOrigin(object):
    def __init__(self, address: (str, int)):
        self.address = address


class SharingClientInfo(object):
    def __init__(self, unique_id: str, sockname: tuple[str, int]):
        self.unique_id = unique_id
        self.ip, self.port = sockname

    def __eq__(self, other):
        if isinstance(other, SharingClientInfo):
            return self.unique_id == other.unique_id and self.ip == other.ip and self.port == other.port
        return False


class SharedFile(object):
    def __init__(self, unique_id: str, name: str, modification_time: int, size: int, origins: list[SharingClientInfo]):
        self.unique_id = unique_id
        self.name = name
        self.modification_time = modification_time
        self.size = size
        self.origins = origins


class SharedFileInfo(object):
    def __init__(self, unique_id: str, sharing_clients: list[SharingClientInfo]):
        self.unique_id = unique_id
        self.sharing_clients = sharing_clients


class FileObject(object):
    """
    A class which represents a shared file during the download/upload stage.
    It can be used by both the sharing client to transfer chunks of it to the downloading client,
    and by the downloading to receive and write chunks into its own local copy of the file.
    """
    CHUNK_SIZE = 1024 * 1024 * 3  # 3 MB

    def __init__(self, file_path: str, files_data: SharedFile = None, is_local: bool = False):
        self._file_path = file_path
        self._files_data = {}
        self._chunk_num = None
        self._downloaded_chunks = 0  # amount of chunks already present in the file
        if is_local:
            self._get_file_data()
        elif files_data is not None:
            self._get_data_from_shared_file(files_data)
            self._write_empty_file()
        else:
            raise ValueError('Bad usage: file is not local and file data was not supplied!')
        self._chunks = set([chunk_num for chunk_num in range(self.amount_of_chunks)])

    def _write_empty_file(self):
        """
        Write null-bytes into the file according to its expected size.
        This is necessary since we want to later overwrite these bytes in place.
        """
        bytes_written = 0
        with open(self._file_path, 'wb') as f:
            while bytes_written < self._files_data['size']:
                bytes_to_write = min(self.CHUNK_SIZE, self._files_data['size'] - bytes_written)
                f.write(bytes(bytes_to_write))
                bytes_written += bytes_to_write

    @property
    def amount_of_chunks(self):
        """
        Total amount of chunks in the file.
        """
        if self._chunk_num is None:
            self._chunk_num = ceil(self._files_data['size'] / self.CHUNK_SIZE)
        return self._chunk_num

    @property
    def downloaded_chunks(self):
        return self._downloaded_chunks

    def _get_file_data(self):
        file_stats = os.stat(self._file_path)
        self._files_data['name'] = os.path.basename(self._file_path)
        self._files_data['modification_time'] = int(file_stats.st_mtime)
        self._files_data['size'] = file_stats.st_size
        self._files_data['unique_id'] = self.get_file_hash()

    def _get_data_from_shared_file(self, files_data: SharedFile):
        self._files_data['name'] = files_data.name
        self._files_data['modification_time'] = files_data.modification_time
        self._files_data['size'] = files_data.size
        self._files_data['unique_id'] = files_data.unique_id

    def get_file_hash(self) -> str:
        """
        Calculates the hash of a local file's data by reading chunks of it and feeding them to the md5 algorithm.
        :return an hexadecimal representation of the file's hash.
        """
        current_md5 = hashlib.md5()
        for i in range(self.amount_of_chunks):
            chunk_data = self.read_chunk(i)
            current_md5.update(chunk_data)
        return current_md5.hexdigest()

    def read_chunk(self, chunk_num: int) -> bytes:
        assert chunk_num < self.amount_of_chunks
        chunk_data = None
        try:
            with open(self._file_path, 'rb+') as f:
                f.seek(self.CHUNK_SIZE * chunk_num)
                chunk_data = f.read(self.CHUNK_SIZE)
        finally:
            assert chunk_data is not None
            return chunk_data

    def write_chunk(self, chunk_num: int, chunk_data: bytes):
        """
        Writes chunk_data into the local file at chunk_num * CHUNK_SIZE offset.
        NOTE: This function merely overwrites existing data in the file, and does not increase the file size.
        """
        assert chunk_num < self.amount_of_chunks
        assert len(chunk_data) <= self.CHUNK_SIZE
        with open(self._file_path, 'r+b') as f:
            f.seek(self.CHUNK_SIZE * chunk_num)
            f.write(chunk_data)
        self._downloaded_chunks += 1
        logger.debug(f'Wrote chunk {chunk_num} to file {self._file_path}')

    def get_shared_file(self):
        return SharedFile(self._files_data['unique_id'],  self._files_data['name'], self._files_data['modification_time'], self._files_data['size'],
                                 []) 

    def get_empty_chunk(self) -> Optional[int]:
        if len(self._chunks) > 0:
            return self._chunks.pop()
        return None

    def has_empty_chunks(self) -> bool:
        """
        Returns whether the files has been completely downloaded.
        """
        return self._downloaded_chunks != self.amount_of_chunks

    def return_failed_chunk(self, chunk_num: int):
        self._chunks.add(chunk_num)
