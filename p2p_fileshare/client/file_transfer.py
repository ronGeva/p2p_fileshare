"""
This module contains the implementation of the local sharing/downloading logic.
"""

import random
from threading import Thread, Event
from p2p_fileshare.framework.channel import Channel


class FileDownloader(object):
    def __init__(self, file_info: SharedFileInfo, server_channel: Channel, local_path: str):
        self._file_info = file_info
        self._server_channel = server_channel
        self._local_path = local_path
        self._stop_event = Event()
        self._chunk_downloaders = []
        self._thread = Thread(target=self.__start)
        ## TODO?: Add chunks md5s to file info and give it to file_object
        self._file_object = DownloadedFileObject(self._local_path)
        #self._file_object.verify_all_chunks() ## ?? maybe do it in FileObject init
        self._thread.start()

    def _check_chunk_downloaders(self):
        for chunk_downloader in self._chunk_downloaders:
            #if chunk finished: TODO - Add the ability to kill blocking downloader
            if not chunk_downloader.is_alive():
                # verify chunk with server
                if self._file_object.verify_chunk(chunk_downloader.chunk):
                    self._server_channel.update_successful_download(self._file_id, chunk_downloader.chunk, chunk_downloader.client_id)
                else:
                    self._server_channel.update_unsuccessful_download(self._file_id, chunk_downloader.chunk, chunk_downloader.client_id)
                # remove from downloaders
                del self._chunk_downloaders[self._chunk_downloaders.index(chunk_downloader)]
            else:
                time.sleep(1)

    def _choose_origin(self):
        # TODO: Make better logic, and maybe ask the server for the best origin
        origin = random.choice(self._file_info.sharing_clients)
        # TODO: Add origin ID to SharedFileInfo so we can update the server on the successful download
        #return origin.id, (origin.ip, origin.port)
        return (origin.ip, origin.port)

    def _run_chunk_downloaders(self):
        if len(self._chunk_downloaders) < MAX_CHUNK_DOWNLOADERS:
            client_addr = self._choose_origin()  #ask server for new chunk download_server
            client_id = 'NOT_USED TODO: make use'
            # start ChunkDownloader
            chunk_downloader = ChunkDownloader(self._file_info.unique_id, client_id, client_addr, self._file_object)
            self._chunk_downloaders.append(chunk_downloader)
            chunk_downloader.start()

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        self._initialize_file_download()
        while not self._stop_event.is_set():
            ## check threads
            self._check_chunk_downloaders()
            self._run_chunk_downloaders()

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
    def __init__(self, file_id: str, client_id: str, client_addr: tuple, file_object: FileObject):
        super().__init__()
        self._file_id = file_id
        self._client_id = client_id
        self._client_addr = client_addr
        self._file_object = file_object
        self._chunk = self._file_object.get_empty_chunk() #find needed chunk
        self._stop_event = Event()
        self._channel = None

    def _init_downloader(self):
        self._channel = socket(...)
        self._channel.connect()

    def run(self):
        self._init_downloader()
        # send get_chunk_message
        # Non blocking recv
            #???? how to make sure get chunk doesn't block so you can stop on signal set
        self._file_object.write_chunk(chunk, data) # Make sure there is timeout on this in file object
        self._stop()

    @property
    def chunk(self):
        return self._chunk

    @property
    def client_id(self):
        return self._client_id

    def stop(self)
        self._stop_event.set()
        time.sleep(1)
        self._stop()

    def _stop(self)
        self._channel.close()