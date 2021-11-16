"""
A module containing different types used by the application
"""
# TODO: consider using NamedTuple for this
from filelock import FileLock

class FileOrigin(object):
    def __init__(self, address: (str, int)):
        self.address = address
        # TODO: consider adding RTT - what does it mean for the server though?


class SharedFile(object):
    def __init__(self, unique_id: str, name: str, modification_time: int, size: int, origins: list):
        self.unique_id = unique_id
        self.name = name
        self.modification_time = modification_time
        self.size = size
        self.origins = origins


class SharingClientInfo(object):
    def __init__(self, sockname: tuple[str, int]):
        self.ip, self.port = sockname


class SharedFileInfo(object):
    def __init__(self, unique_id: str, sharing_clients: list[SharingClientInfo]):
        self.unique_id = unique_id
        self.sharing_clients = sharing_clients


class FileObject(object):
    CHUNK_SIZE = 1024*1024*3
    def __init__(self, file_path: str, files_data: SharedFile =None, new_file: bool =False):
        self._file_path = file_path
        self._files_data = {}
        self._file_lock = FileLock(self._file_path+'.lock')
        if new_file:
            self._get_file_data()
        else:
            self._get_data_from_shared_file(files_data)
        self._chunk_mum = None
        self._chunks = {}

    @property
    def chunk_mum(self):
        if self._chunk_mum is None:
            self._chunk_mum = int(self._files_data['size'] / self.CHUNK_SIZE)
            if self._files_data['size'] % self.CHUNK_SIZE != 0:
                self._chunk_mum += 1
        return self._chunk_mum

    def _get_file_data(self):
        #unique_id, name, modification_time, size, origins
        file_stats = os.stat(file_path)
        self._files_data['name'] = os.path.basename(file_path)
        self._files_data['modification_time'] = int(file_stats.st_mtime)
        self._files_data['size'] = file_stats.st_size
        self._files_data['unique_id'] = get_file_hash(file_path)

    def _get_data_from_shared_file(self, files_data: SharedFile):
        self._files_data['name'] = files_data.name
        self._files_data['modification_time'] = files_data.modification_time
        self._files_data['size'] = files_data.size
        self._files_data['unique_id'] = files_data.unique_id

    def update_db(self):
        pass

    def get_chunk_md5(self, chunk: int) -> str:
        assert chunk < self.chunk_mum
        current_md5 = hashlib.md5()
        chunk_data = self.read_chunk(chunk)
        current_md5.update(chunk_data)
        return current_md5.hexdigest()

    def get_file_hash(self) -> str:
        """
        Calculates the hash of a local file's data by reading chunks of it and feeding them to the md5 algorithm.
        :return an hexadecimal representation of the file's hash.
        """
        current_md5 = hashlib.md5()
        for i in range(self.chunk_mum):
            chunk_data = self.read_chunk(i)
            current_md5.update(chunk_data)
        return current_md5.hexdigest()

    def verify_all_chunks(self, chunks_md5: dict):
        for i in range(self.chunk_mum):
            if i in self._chunks and self._chunks[i] is None:
                self._chunks.pop(i)
        for chunk, chunk_md5 in chunks_md5.items():
            if not self.verify_chunk(chunk, chunk_md5):
                # log and update db on corrupted chunk
                return False
        return True

    def verify_chunk(self, chunk: int, md5: str):
        return True
        assert self.get_chunk_md5(chunk) == md5

    def read_chunk(self, chunk: int):
        assert chunk < self.chunk_mum
        self._file_lock.acquire()
        chunk_data = None
        try:
            with open(self._file_path, 'rb+') as f:
                f.seek(self.CHUNK_SIZE*chunk)
                chunk_data = f.read(self.CHUNK_SIZE)
        finally:
            self._file_lock.release()
            assert chunk_data is not None
            return chunk_data

    def write_chunk(self, chunk: int, chunk_data: str):
        assert chunk < self.chunk_mum
        assert len(chunk_data) <= self.CHUNK_SIZE
        self._file_lock.acquire()
        try:
            with open(self._file_path, 'rb+') as f:
                f.seek(self.CHUNK_SIZE*chunk)
                f.write(chunk_data)
        finally:
            self._chunks[chunk] = True
            self._file_lock.release()

    def get_shared_file(self):
        return SharedFile(self._files_data['unique_id'],  self._files_data['name'], self._files_data['modification_time'], self._files_data['size'],
                                 []) 

    def get_empty_chunk(self):
        for i in range(self.chunk_mum):
            if i not in self._chunks:
                return i
        return None

    def lock_chunk(self, chunk):
        self._chunks[chunk] = None
