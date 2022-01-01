from p2p_fileshare.client.files_manager import FilesManager
from p2p_fileshare.server.server import MetadataServer
from p2p_fileshare.client.file_transfer import FileDownloader
from p2p_fileshare.framework.types import SharedFile
from utils import LogStashHandler
from contextlib import contextmanager
from unittest.mock import Mock
import tempfile
import os
import time
import logging


@contextmanager
def closed_temporary_file() -> tempfile.TemporaryFile:
    """
    :return: A closed temporary file which is guaranteed to exist and to be deleted once the context manager exits.
    """
    with tempfile.TemporaryFile(delete=False) as tf:
        tf.close()
        try:
            yield tf
        finally:
            os.unlink(tf.name)


@contextmanager
def _prepare_for_download(first_client: FilesManager, second_client: FilesManager) -> (SharedFile,
                                                                                       tempfile._TemporaryFileWrapper,
                                                                                       bytes):
    """
    Prepare the environment for file download.
    This function creates a file with random data, share it via first_client, searches it via second_client, get the
    SharedFile object representing the file via second_client and prepare a temporary file to downlaod the file into.
    :param first_client: The client which we'll use to share the file.
    :param second_client: The client which we'll use to search the file.
    :return: a 3 tuple containing - (the requested file <SharedFile>, the output file <TemporaryFile>, the data of the
    file shared <bytes>).
    """
    with closed_temporary_file() as first_client_file:
        first_data = os.urandom(100)
        with open(first_client_file.name, 'wb') as f:
            f.write(first_data)
        first_client.share_file(first_client_file.name)
        time.sleep(1)  # wait a bit so that the server will update its DB
        res = second_client.search_file(os.path.basename(first_client_file.name))
        assert len(res) == 1, "Expected to find only searched file, instead got: {0}".format(res)
        requested_file = res[0]
        with closed_temporary_file() as second_client_file:
            yield requested_file, second_client_file, first_data


def test_simple_file_transfer(metadata_server: MetadataServer, first_client: FilesManager, second_client: FilesManager):
    """
    Test the file transfer works in its simplest form.
    Steps:
    1. Create a file with 100 bytes of random data.
    2. Share the file created in step #1 via client #1 (and wait a bit for the server to process the request).
    3. Search the file shared in step #2 via client #2.
    4. Download the file found via client #2.
    5. Wait for the download initiated in step #4 to finish.
    6. Assert the file was downloaded successfully.
    """
    with _prepare_for_download(first_client, second_client) as params:
        requested_file, second_client_file, file_data = params
        second_client.download_file(requested_file.unique_id, second_client_file.name)
        download = second_client.list_downloads()[0]
        while not download.is_done():
            continue
        assert not download.failed, "Download failed!"
        with open(second_client_file.name, 'rb') as f:
            second_data = f.read()
        assert file_data == second_data, "File's data is different after transfer. Expected: {0}, got: {1}". \
            format(file_data, second_data)


def test_transfer_timeout(metadata_server: MetadataServer, first_client: FilesManager, second_client: FilesManager):
    """
    Test the FileDownloader's timeout mechanism works as intended.
    First we set up the download environment (share a file via the first client, search it via the second client).
    We then override's the sharing client chunk transferring function so that it will do nothing but hold the socket
    (thus simulating real life hung situation where the other endpoint does no respond).
    We then attempt to download the file and expect the download to fail.
    Finally, we make sure the file_transfer module has logged a timeout error (to validate the download failed due to
    a timeout).
    """
    saved_client = []
    def _mock_receive_new_client(client, client_address, finished_socket):
        # "Save" the socket inside a local variable so it won't be deleted, causing the connection to fail
        # when the test exits, the socket will be released and destroyed
        saved_client.append(client)
        # Return a mock object to the sharing client
        return Mock()
    file_transfer_logger = logging.getLogger('p2p_fileshare.client.file_transfer')
    log_stash = LogStashHandler()
    file_transfer_logger.addHandler(log_stash)

    with _prepare_for_download(first_client, second_client) as download_params:
        requested_file, second_client_file, _ = download_params
        # Cause the first client's share server to do nothing with new clients, in order to trigger a timeout
        first_client._file_share_server._receive_new_client = _mock_receive_new_client

        second_client.download_file(requested_file.unique_id, second_client_file.name)
        download = second_client.list_downloads()[0]
        download.CHUNK_TIMEOUT = 3  # set the timeout to be small
        start_time = time.time()
        # Give the FileDownloader 3 more seconds to avoid a race condition
        while not download.is_done() and time.time() - start_time < FileDownloader.RTT_TIMEOUT + FileDownloader.CHUNK_TIMEOUT + 3:
            continue
        assert download.failed, "Download has not failed!"
    # Make sure a timeout has occurred by viewing the logs of file_transfer.py
    assert any(["due to timeout" in record.msg for record in log_stash.logs])
