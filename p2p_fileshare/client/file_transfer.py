"""
This module contains the implementation of the local sharing/downloading logic.
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
        ## TODO?: Add chunks md5s to file info and give it to file_object
        self._file_object = FileObject(self._local_path, self._file_info)
        #self._file_object.verify_all_chunks() ## ?? maybe do it in FileObject init
        self._thread.start()

    def _initialize_file_download(self):
        pass

    def _check_chunk_downloaders(self):
        for chunk_downloader in self._chunk_downloaders:
            #if chunk finished: TODO - Add the ability to kill blocking downloader
            print('Checking downloaders', flush=True)
            if not chunk_downloader.is_alive():
                print('Removing downloader', flush=True)
                # verify chunk with server
                if self._file_object.verify_chunk(chunk_downloader.chunk, None):
                    download_update_message = SuccessfulChunkDownloadUpdateMessage(self._file_id, chunk_downloader.chunk, chunk_downloader.client_id)
                else:
                    download_update_message = SuccessfulChunkDownloadUpdateMessage(self._file_id, chunk_downloader.chunk, chunk_downloader.client_id)
                self._server_channel.send_message(download_update_message)
                # remove from downloaders
                del self._chunk_downloaders[self._chunk_downloaders.index(chunk_downloader)]

    def _choose_origin(self, origin_chunk):
        got_origin = False
        for i in range(10):
        # TODO: Make better logic, and maybe ask the server for the best origin
            origin = random.choice(self._file_info.origins)
        # TODO: Add origin ID to SharedFileInfo so we can update the server on the successful download
        #return origin.id, (origin.ip, origin.port)
            if origin.ip is not None and origin.port is not None:
                return (origin.ip, origin.port)
        raise Exception('Coun\'nt find an origin to download the file')

    def _run_chunk_downloaders(self):
        if len(self._chunk_downloaders) < self.MAX_CHUNK_DOWNLOADERS:
            empty_chunk = self._file_object.get_empty_chunk() #find needed chunk
            if empty_chunk is None:
                self._stop_event.set()
                return
            client_addr = self._choose_origin(empty_chunk)  #ask server for new chunk download_server
            client_id = 'NOT_USED TODO: make use'
            print(f"{client_addr} was chosen for chunk {empty_chunk} download", flush=True)
            # start ChunkDownloader
            chunk_downloader = ChunkDownloader(self._file_info.unique_id, client_id, client_addr, self._file_object, empty_chunk)
            self._chunk_downloaders.append(chunk_downloader)
            print('starting new downloader', flush=True)
            chunk_downloader.start()

    def is_done(self):
        return self._stop_event.is_set()

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        self._initialize_file_download()
        while not self.is_done():
            ## check threads
            self._check_chunk_downloaders()
            self._run_chunk_downloaders()
            time.sleep(1)


    def stop(self):
        self._stop_event.set()
        for chunk_downloader in self._chunk_downloaders:
            if chunk_downloader.is_alive():
                chunk_downloader.join(timeout=10)
                if chunk_downloader.is_alive():
                    chunk_downloader.abort()

    def __stop(self):
        """
        Stops the channel's thread and signal the main Server component that this channel is invalid.
        """
        raise NotImplementedError


class ChunkDownloader(Thread):
    def __init__(self, file_id: str, client_id: str, client_addr: tuple, file_object: FileObject, chunk_num: int):
        super().__init__()
        self._file_id = file_id
        self._client_id = client_id
        self._client_addr = client_addr
        self._file_object = file_object
        self._chunk =  chunk_num
        self._stop_event = Event()
        self._channel = None

    def _init_downloader(self):
        s = socket()
        s.connect(self._client_addr)
        print(f'Connected to {self._client_addr}', flush=True)
        self._channel = Channel(s, self._stop_event)

    def _get_chunk_data(self):
        download_message = StartFileTransferMessage(file_id=self._file_id, chunk_num=self.chunk)
        chunk_download_response = self._channel.send_msg_and_wait_for_response(download_message)
        return chunk_download_response.data

    def run(self):
        print('Starting thread', flush=True)
        # send get_chunk_message
        # Non blocking recv
            #???? how to make sure get chunk doesn't block so you can stop on signal set
        self._init_downloader()
        self._file_object.lock_chunk(self.chunk)
        print(f'Getting chunk', flush=True)
        data = self._get_chunk_data()
        print(f'Got chunk', flush=True)
        self._file_object.write_chunk(self.chunk, data) # Make sure there is timeout on this in file object
        print(f'Wrote chunk', flush=True)
        self._file_object.verify_chunk(self.chunk, None)
        self._stop()

    @property
    def chunk(self):
        return self._chunk

    @property
    def client_id(self):
        return self._client_id

    def stop(self):
        self._stop_event.set()
        time.sleep(1)
        self._stop()

    def _stop(self):
        print(type(self._channel), flush=True)
        if self._channel is not None:
            self._channel.close()