"""
This module contains the implementation of the local downloading logic.
"""

import time
import random
from socket import socket
from threading import Thread, Event
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.types import FileObject, SharedFile
from p2p_fileshare.framework.messages import StartFileTransferMessage


class FileDownloader(object):
    MAX_CHUNK_DOWNLOADERS = 2

    def __init__(self, file_info: SharedFile, server_channel: Channel, local_path: str):
        self._file_info = file_info
        self._server_channel = server_channel
        self._local_path = local_path
        self._stop_event = Event()
        self._chunk_downloaders = []
        self._thread = Thread(target=self.__start)
        self._file_object = FileObject(self._local_path, self._file_info)
        self._thread.start()

    def _check_chunk_downloaders(self):
        downloaders_to_remove = []
        for chunk_downloader in self._chunk_downloaders:
            # TODO - Add the ability to kill blocking downloader
            if chunk_downloader.finished:
                downloaders_to_remove.append(chunk_downloader)

        for downloader_to_remove in downloaders_to_remove:
            self._chunk_downloaders.remove(downloader_to_remove)

    def _choose_origin(self, chunk_num):
        """
        Retrieves the best origin from which to download the file chunk.
        """
        # TODO: improve this logic to consider RTT
        for origin in self._file_info.origins:
            if origin.ip is not None and origin.port is not None:
                return origin.ip, origin.port
        raise Exception('Coun\'nt find an origin to download the file')

    def _run_chunk_downloaders(self):
        if len(self._chunk_downloaders) < self.MAX_CHUNK_DOWNLOADERS:
            chunk_num = self._file_object.get_empty_chunk()  # find needed chunk
            if chunk_num is None:
                # we're finished
                return
            client_addr = self._choose_origin(chunk_num)  # ask server for new chunk download_server
            # start ChunkDownloader
            chunk_downloader = ChunkDownloader(self._file_info.unique_id, client_addr, self._file_object, chunk_num)
            self._chunk_downloaders.append(chunk_downloader)
            chunk_downloader.start()

    def is_done(self):
        return self._stop_event.is_set() or not self._file_object.has_empty_chunks()

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        while not self.is_done():
            # check threads
            self._check_chunk_downloaders()
            self._run_chunk_downloaders()
            time.sleep(1)

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


class ChunkDownloader(Thread):
    def __init__(self, file_id: str, client_addr: tuple, file_object: FileObject, chunk_num: int):
        super().__init__()
        self._file_id = file_id
        self._client_addr = client_addr
        self._file_object = file_object
        self._chunk = chunk_num
        self.stop_event = Event()
        self._channel = None
        self.finished = False

    def _init_downloader(self):
        s = socket()
        s.connect(self._client_addr)
        self._channel = Channel(s, self.stop_event)

    def _get_chunk_data(self) -> bytes:
        download_message = StartFileTransferMessage(file_id=self._file_id, chunk_num=self.chunk)
        chunk_download_response = self._channel.send_msg_and_wait_for_response(download_message)
        return chunk_download_response.data

    def run(self):
        try:
            self._init_downloader()
            self._file_object.lock_chunk(self.chunk)
            data = self._get_chunk_data()
            self._file_object.write_chunk(self.chunk, data)  # Make sure there is timeout on this in file object
        except Exception as e:
            self._file_object.unlock_chunk(self.chunk)  # something went wrong - we still need to download this chunk
            raise e
        finally:
            self.stop()

    @property
    def chunk(self):
        return self._chunk

    def stop(self):
        self.stop_event.set()
        time.sleep(1)
        self._stop()

    def _stop(self):
        if self._channel is not None:
            self._channel.close()
        self.finished = True
