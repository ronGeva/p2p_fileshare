"""
This module contains the implementation of the local sharing/downloading logic.
"""
from threading import Thread, Event
from p2p_fileshare.framework.channel import Channel


class FileDownloader(object):
    def __init__(self, file_id: str, server_channel: Channel, local_path: str):
        self._file_id = file_id
        self._server_channel = server_channel
        self._local_path = local_path
        self._stop_event = Event()
        self._chunk_downloaders = []
        self._file_data = None
        self._file_object = None
        self._thread = Thread(target=self.__start)
        self._thread.start()

    def _initialize_file_download(self):
        self._file_data = self._server_channel.get_file_data(self._file_id) #get_file_data_from_server

        if self._file_data is invalid:
            self.stop()

        self._file_object = FileObject(self._file_data, self._local_path)
        self._file_object.verify_all_chunks() ## ?? maybe do it in FileObject init

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        self._initialize_file_download()
        while not self._stop_event.is_set():
            ## check threads
            for chunk_downloader in self._chunk_downloaders:
                #if chunk finished:
                if not chunk_downloader.is_alive():
                    # verify chunk with server
                    if self._file_object.verify_chunk(chunk_downloader._chunk):
                        self._server_channel.update_successful_download(self._file_id, chunk_downloader._chunk, chunk_downloader._client_id)
                    else:
                        self._server_channel.update_unsuccessful_download(self._file_id, chunk_downloader._chunk, chunk_downloader._client_id)

                    chunk_downloader.stop()
                    # remove from downloaders
                    del self._chunk_downloaders[self._chunk_downloaders.index(chunk_downloader)]
                else:
                    time.sleep(1)
            else:
                sleep
            if len(self._chunk_downloaders) < MAX_CHUNK_DOWNLOADERS:
                needed_chunk = self._file_object.get_empty_chunk() #find needed chunk
                client_id, client_addr = self.server_channel.get_chunk_server(file_id, needed_chunk)  #ask server for new chunk download_server
                chunk_downloader = ChunkDownloader(self._file_id, needed_chunk, client_id, client_addr, self._file_object) #start ChunkDownloader
                self._chunk_downloaders.append(chunk_downloader)
                chunk_downloader.start()

    def stop(self):
        self._stop_event.set()
        for chunk_downloader in self._chunk_downloaders:
            if chunk_downloader.is_alive():
                chunk_downloader.stop()
                chunk_downloader.join(timeout=10)
                if chunk_downloader.is_alive():
                    chunk_downloader.abort()

    def __stop(self):
        """
        Stops the channel's thread and signal the main Server component that this channel is invalid.
        """
        raise NotImplementedError


class ChunkDownloader(Thread):
    def __init__(self, file_id: str, chunk: int, client_id: str, client_addr: tuple, file_object: FileObject):
        self._file_id = file_id
        self._chunk = chunk
        self._client_id = client_id
        self._client_addr = client_addr
        self._file_object = file_object
        self._channel = None

    def _init_downloader(self):
        self._channel = socket(...)
        self._channel.connect()

    def run(self):
        self._init_downloader()
        send get_chunk_message
        #???? how to make sure get chunk doesn't block so you can stop on signal set
        self._file_object.write_chunk(chunk, data)
        self._stop()

    def stop(self)
        self._stop_event.set()

    def _stop(self)
        self._channel.close()