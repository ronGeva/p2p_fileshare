"""
This module contains the implementation of the local downloading logic.
"""

import time
from socket import socket
from threading import Thread, Event
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.types import FileObject, SharedFile, SharingClientInfo
from p2p_fileshare.framework.messages import StartFileTransferMessage


class FileDownloader(object):
    """
    A class responsible for governing the file downloading operation from different origins.
    The FileDownloader creates and monitors instances of ChunkDownloader until either the requested file is successfully
    downloaded or a fatal error occurs.
    """
    MAX_CHUNK_DOWNLOADERS = 2
    CHUNK_TIMEOUT = 5

    def __init__(self, file_info: SharedFile, server_channel: Channel, local_path: str):
        self._file_info = file_info
        self._server_channel = server_channel
        self._local_path = local_path
        self._stop_event = Event()
        self._chunk_downloaders = []
        self._thread = Thread(target=self.__start)
        self._file_object = FileObject(self._local_path, self._file_info)
        self._thread.start()

    @property
    def progress(self) -> int:
        """
        Retrieve a number between 0 to 100 representing the percentage of the file successfully downloaded until now.
        """
        return int((self._file_object.downloaded_chunks / self._file_object.amount_of_chunks) * 100)

    @property
    def local_path(self):
        return self._local_path

    @property
    def file_info(self):
        return self._file_info

    def _check_chunk_downloaders(self):
        downloaders_to_remove = []
        current_time = time.time()
        for chunk_downloader in self._chunk_downloaders:
            # TODO - Add the ability to kill blocking downloader
            if chunk_downloader.finished:
                if chunk_downloader.failed:
                    # Something failed, let's stop downloading from this origin
                    self._remove_origin(chunk_downloader)
                downloaders_to_remove.append(chunk_downloader)
            elif current_time - chunk_downloader.start_time > self.CHUNK_TIMEOUT:
                chunk_downloader.stop()
                self._remove_origin(chunk_downloader)
                downloaders_to_remove.append(chunk_downloader)

        for downloader_to_remove in downloaders_to_remove:
            self._chunk_downloaders.remove(downloader_to_remove)

    def _remove_origin(self, chunk_downloader: "ChunkDownloader"):
        """
        Removes the origin of chunk_downloader, if it's still in the file's origins.
        """
        if chunk_downloader.origin in self._file_info.origins:
            self._file_info.origins.remove(chunk_downloader.origin)

    def _choose_origin(self, chunk_num) -> SharingClientInfo:
        """
        Retrieves the best origin from which to download the file chunk.
        """
        # TODO: improve this logic to consider RTT
        for origin in self._file_info.origins:
            if origin.ip is not None and origin.port is not None:
                return origin
        raise Exception('Coun\'nt find an origin to download the file')

    def _run_chunk_downloaders(self):
        if len(self._chunk_downloaders) < self.MAX_CHUNK_DOWNLOADERS:
            chunk_num = self._file_object.get_empty_chunk()  # find needed chunk
            if chunk_num is None:
                # we're finished
                return
            origin = self._choose_origin(chunk_num)
            # start ChunkDownloader
            chunk_downloader = ChunkDownloader(self._file_info.unique_id, origin, self._file_object, chunk_num)
            self._chunk_downloaders.append(chunk_downloader)
            chunk_downloader.start()

    def is_done(self):
        return self._stop_event.is_set() or not self._file_object.has_empty_chunks()

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        try:
            while not self.is_done():
                # check threads
                self._check_chunk_downloaders()
                self._run_chunk_downloaders()
                time.sleep(1)
        except Exception as e:
            self._stop_event.set()  # let the app know the download failed
            raise e

    def stop(self):
        """
        Stops the main file downloading thread as well as all chunk downloading threads.
        """
        self._stop_event.set()
        for chunk_downloader in self._chunk_downloaders:
            if chunk_downloader.is_alive():
                chunk_downloader.stop_event.set()
                chunk_downloader.join(timeout=1)
                if chunk_downloader.is_alive():
                    chunk_downloader.abort()

    @property
    def failed(self):
        # If the stop event was set and the file wasn't fully downloaded we can determine the download failed
        return self._stop_event.is_set() and self._file_object.has_empty_chunks()


class ChunkDownloader(Thread):
    """
    A class responsible for governing the download of a single file chunk.
    """
    def __init__(self, file_id: str, origin: SharingClientInfo, file_object: FileObject, chunk_num: int):
        super().__init__()
        self._file_id = file_id
        self.origin = origin
        self._file_object = file_object
        self._chunk_num = chunk_num
        self.stop_event = Event()
        self._channel = None
        self.finished = False
        self.failed = False
        self.start_time = None

    def _init_downloader(self):
        s = socket()
        s.connect((self.origin.ip, self.origin.port))
        self._channel = Channel(s, self.stop_event)

    def _get_chunk_data(self) -> bytes:
        download_message = StartFileTransferMessage(file_id=self._file_id, chunk_num=self._chunk_num)
        chunk_download_response = self._channel.send_msg_and_wait_for_response(download_message)
        return chunk_download_response.data

    def run(self):
        self.start_time = time.time()
        try:
            self._init_downloader()
            data = self._get_chunk_data()
            self._file_object.write_chunk(self._chunk_num, data)  # Make sure there is timeout on this in file object
        except Exception as e:
            # Something went wrong - we still need to download this chunk
            self._file_object.return_failed_chunk(self._chunk_num)
            self.failed = True
            raise e
        finally:
            self.stop()

    def stop(self):
        """
        Stops the chunk downloading thread and closes its underlying channel.
        """
        self.stop_event.set()
        time.sleep(1)
        if self._channel is not None:
            self._channel.close()
        self.finished = True
