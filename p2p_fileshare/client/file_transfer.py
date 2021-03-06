"""
This module contains the implementation of the local downloading logic.
"""

import time
import logging
from socket import socket
from threading import Thread, Event
from typing import Optional
from p2p_fileshare.framework.channel import Channel, TimeoutException
from p2p_fileshare.framework.types import FileObject, SharedFile, SharingClientInfo
from p2p_fileshare.framework.messages import StartFileTransferMessage, SharingInfoRequestMessage, SharingInfoResponseMessage, RTTCheckMessage


logger = logging.getLogger(__name__)


RTTInfo = tuple[SharingClientInfo, tuple[float, float]]


class FileDownloader(object):
    """
    A class responsible for governing the file downloading operation from different origins.
    The FileDownloader creates and monitors instances of ChunkDownloader until either the requested file is successfully
    downloaded or a fatal error occurs.
    """
    MAX_CHUNK_DOWNLOADERS = 2
    RTT_TIMEOUT = 2
    RTT_TOLERANCE = 0.5
    CHUNK_TIMEOUT = 5
    MIN_ORIGINS_FOR_UPDATE = 10
    MAX_ORIGIN_DOWNLOADER = 2
    MAX_ORIGIN_FAILS = 5

    def __init__(self, file_info: SharedFile, server_channel: Channel, local_path: str):
        self._file_info = file_info
        self._server_channel = server_channel
        self._local_path = local_path
        self._stop_event = Event()
        self._is_done = False
        self._chunk_downloaders = []
        self._origins_stats = {}
        self._thread = Thread(target=self.__start)
        self._file_object = FileObject(self._local_path, self._file_info)
        self._thread.start()

    @property
    def progress(self) -> int:
        """
        Retrieve a number between 0 to 100 representing the percentage of the file successfully downloaded until now.
        """
        return int((len(self._file_object.downloaded_chunks) / self._file_object.amount_of_chunks) * 100)

    @property
    def local_path(self):
        return self._local_path

    @property
    def file_info(self):
        return self._file_info

    def _update_origin_stat_after_download(self, downloader: "ChunkDownloader"):
        """
        After a single ChunkDownloader has finished operating, update the statistics of its origin so that we can
        choose a new origin more wisely in the future (for example if the download was extremely slow we can later
        choose to download from a different origin).
        :param downloader: The finished ChunkDownloader.
        :return: None
        """
        logger.debug(f"Updating stats after download: {downloader.origin}")
        origin_stats = self._origins_stats[downloader.origin]
        origin_stats['downloaders'] = origin_stats['downloaders'] - 1
        if not downloader.failed:
            origin_stats['failed_attempts'] = 0
            download_time = time.time() - downloader.start_time
            score = origin_stats['score']
            if score is None:
                origin_stats['score'] = (download_time, 1)
            else:
                origin_stats['score'] = (((score[0] * score[1]) + download_time) / (score[1]+1), score[1] + 1)
        else:
            origin_stats['failed_attempts'] = origin_stats['failed_attempts'] + 1

    def _check_chunk_downloaders(self):
        """
        Iterates the current running chunk downloaders and handles hung / finished ones.
        A hung downloader should be stopped and be treated as a failed one.
        A finished downloader should be removed from the current running downloaders and have its origin statistics
        updated according to the result of the download.
        """
        downloaders_to_remove = []
        current_time = time.time()
        logger.debug("Checking chunk downloaders")
        for chunk_downloader in self._chunk_downloaders:
            if chunk_downloader.finished:
                downloaders_to_remove.append(chunk_downloader)
            elif current_time - chunk_downloader.start_time > self.CHUNK_TIMEOUT:
                logger.error("Stopping ChunkDownloader {0} due to timeout.".format(chunk_downloader))
                chunk_downloader.failed = True
                chunk_downloader.stop()
                downloaders_to_remove.append(chunk_downloader)

        for downloader_to_remove in downloaders_to_remove:
            self._update_origin_stat_after_download(downloader_to_remove)
            if self._origins_stats[downloader_to_remove.origin]['failed_attempts'] >= self.MAX_ORIGIN_FAILS:
                # Origin fails too frequently, let's stop downloading from this origin for now
                self._remove_origin(downloader_to_remove)
            self._chunk_downloaders.remove(downloader_to_remove)

    def _calculate_round_trip_time(self, origin: SharingClientInfo) -> Optional[RTTInfo]:
        """
        Calculate RTT and other network statistics for a single origin.
        :param origin: A SharingClientInfo of a single client that shares the file we're currently downloading.
        :return: A 2-tuple representing an estimation of the time (in seconds) of the time it takes to communicate
        with the origin. First element in the tuple represents the time it takes from us to the origin, and the second
        element represents the time it takes from the origin back to us.
        """
        logger.debug(f'Calculating rtt for {origin.ip}:{origin.port}')
        try:
            s = socket()
            s.settimeout(self.RTT_TIMEOUT)
            s.connect((origin.ip, origin.port))
            rtt_channel = Channel(s)
            rtt_check_message = RTTCheckMessage()
            rtt_check_start = time.time()
            rtt_response_message = rtt_channel.send_msg_and_wait_for_response(rtt_check_message, timeout=self.RTT_TIMEOUT)
            absolute_rtt = time.time() - rtt_check_start
            msg_rtt = (rtt_response_message.recv_time-rtt_response_message.send_time,
                       time.time()-rtt_response_message.recv_time)
            rtt_channel.close()
            if abs(absolute_rtt-(msg_rtt[0]+msg_rtt[1])) > self.RTT_TOLERANCE:
                rtt = msg_rtt
            else:
                rtt = (absolute_rtt/2, absolute_rtt/2)
            return origin, rtt
        except TimeoutException as e:
            logger.error(e)
            return None

    @staticmethod
    def _weight_rtt(rtt_list: list[RTTInfo]) -> list[tuple[SharingClientInfo, float]]:
        return [(rtt[0], rtt[1][0]/2+rtt[1][1]) for rtt in rtt_list if rtt is not None]

    def _update_origins(self):
        """
        If necessary, request a new list of clients that share the file from the server.
        """
        if len(self._origins_stats) < self.MIN_ORIGINS_FOR_UPDATE:
            logger.debug("Updating origin list")
            sharing_info_request = SharingInfoRequestMessage(self._file_info.unique_id)
            self._server_channel.send_message(sharing_info_request)
            shared_file = self._server_channel.wait_for_message(SharingInfoResponseMessage).shared_file
            self._file_info.origins = shared_file.origins

    def _base_rate_origins(self):
        """
        Calculates the RTT to every client which we've yet to run RTT check on.
        """
        origins_rtt = [self._calculate_round_trip_time(origin) for origin in self._file_info.origins if origin not in
                       self._origins_stats]
        weighted_origins_rtt = self._weight_rtt(origins_rtt)
        for origin, rtt in weighted_origins_rtt:
            self._origins_stats[origin] = {'rtt': rtt, 'score': None, 'downloaders': 0, 'failed_attempts': 0}

    def _remove_origin(self, chunk_downloader: "ChunkDownloader"):
        """
        Removes the origin of chunk_downloader, if it's still in the file's origins.
        """
        if chunk_downloader.origin in self._origins_stats:
            self._origins_stats.pop(chunk_downloader.origin)

    def _choose_origin(self) -> Optional[SharingClientInfo]:
        """
        Retrieves the best origin from which to download the file chunk.
        """
        logger.debug("Choosing new origin")
        self._update_origins()
        self._base_rate_origins()

        logger.debug("Choosing based on score")
        # Getting the best score (the lowest avarage chunk download time)
        scored_origins = [origin for origin in self._origins_stats if self._origins_stats[origin]['score'] is not None]
        scored_origins = sorted(scored_origins, key=lambda origin: self._origins_stats[origin]['score'][0])

        for origin in scored_origins:
            if self._origins_stats[origin]['downloaders'] < self.MAX_ORIGIN_DOWNLOADER:
                return origin

        logger.debug("Choosing based on rtt")
        # Choosing the next origin based on rtt (since we used all the scored origins)
        unscored_origins = [(origin, self._origins_stats[origin]['rtt']) for origin in self._origins_stats if self._origins_stats[origin]['score'] is None]
        unscored_origins = sorted(unscored_origins, key=lambda origin: origin[1])
        for origin, rtt in unscored_origins:
            if self._origins_stats[origin]['downloaders'] < self.MAX_ORIGIN_DOWNLOADER:
                return origin

        return None

    def _run_chunk_downloaders(self):
        """
        Initializes new chunks downloaders if it's necessary.
        Each ChunkDownloader is responsible for downloading a single chunk of the file.
        """
        if len(self._chunk_downloaders) < self.MAX_CHUNK_DOWNLOADERS:
            chunk_num = self._file_object.get_empty_chunk()  # find needed chunk
            logger.debug(f"Trying to download chunk: {chunk_num}")
            if chunk_num is None:
                # we're finished
                return

            try:
                origin = self._choose_origin()
                if origin is None:
                    self._file_object.return_failed_chunk(chunk_num)
                    return
            except Exception as e:
                self._file_object.return_failed_chunk(chunk_num)
                raise e

            origin = self._choose_origin()

            logger.debug(f"Choose origin {origin} for chunk_num {chunk_num}")
            self._origins_stats[origin]['downloaders'] = self._origins_stats[origin]['downloaders'] + 1
            # Start ChunkDownloader
            chunk_downloader = ChunkDownloader(self._file_info.unique_id, origin, self._file_object, chunk_num)
            self._chunk_downloaders.append(chunk_downloader)
            chunk_downloader.start()

    def did_finish_download(self):
        return self._stop_event.is_set() or not self._file_object.has_empty_chunks()

    def is_done(self):
        return self._stop_event.is_set()

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        try:
            while not self.did_finish_download():
                # check threads
                self._check_chunk_downloaders()
                self._run_chunk_downloaders()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Got exception: {e}")
        finally:
            self.stop()  # let the app know the download failed

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
        """
        Initiates the udnerlying channel that will be used in the downlaod process.
        """
        s = socket()
        s.connect((self.origin.ip, self.origin.port))
        self._channel = Channel(s, self.stop_event)

    def _get_chunk_data(self) -> bytes:
        """
        Requests and receives the file chunk as a ChunkDataResponseMessage.
        """
        download_message = StartFileTransferMessage(file_id=self._file_id, chunk_num=self._chunk_num)
        chunk_download_response = self._channel.send_msg_and_wait_for_response(download_message)
        return chunk_download_response.data

    def run(self):
        """
        Initiates the communication channel with the remote sharing client, request and download the file chunk and
        handles download errors in case they occur.
        """
        try:
            self.start_time = time.time()
            self._init_downloader()
            logger.debug('Starting chunk download')
            data = self._get_chunk_data()
            logger.debug(f'Got chunk in size {len(data)}')
            self._file_object.write_chunk(self._chunk_num, data)  # Make sure there is timeout on this in file object
            logger.debug(f'Wrote chunk data')
        except Exception as e:
            # Something went wrong - we still need to download this chunk
            self._file_object.return_failed_chunk(self._chunk_num)
            self.failed = True
            logger.error(f'Failed chunk download: {e}')
        finally:
            self.stop()

    def stop(self):
        """
        Stops the chunk downloading thread and closes its underlying channel.
        """
        if self.failed:
            self._file_object.return_failed_chunk(self._chunk_num)
        self.stop_event.set()
        time.sleep(1)
        if self._channel is not None:
            self._channel.close()
        self.finished = True

    def __str__(self):
        return "File ID: {file_id}, origin: {origin}, chunk: {chunk}".format(
            file_id=self._file_id, origin=self.origin, chunk=self._chunk_num
        )
