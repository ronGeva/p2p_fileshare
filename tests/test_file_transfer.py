import time

from p2p_fileshare.client.files_manager import FilesManager
from p2p_fileshare.server.server import MetadataServer
from p2p_fileshare.client.file_transfer import FileDownloader
from contextlib import contextmanager
from unittest.mock import Mock
import tempfile
import os


@contextmanager
def closed_temporary_file():
    """
    :return: A closed temporary file which is guaranteed to exist and to be deleted once the context manager exits.
    """
    with tempfile.TemporaryFile(delete=False) as tf:
        tf.close()
        try:
            yield tf
        finally:
            os.unlink(tf.name)


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
            second_client.download_file(requested_file.unique_id, second_client_file.name)
            download = second_client.list_downloads()[0]
            while not download.is_done():
                continue
            assert not download.failed, "Download failed!"
            with open(second_client_file.name, 'rb') as f:
                second_data = f.read()
            assert first_data == second_data, "File's data is different after transfer. Expected: {0}, got: {1}".\
                format(first_data, second_data)


def test_transfer_timeout(metadata_server: MetadataServer, first_client: FilesManager, second_client: FilesManager):
    with closed_temporary_file() as first_client_file:
        first_data = os.urandom(100)
        with open(first_client_file.name, 'wb') as f:
            f.write(first_data)
        first_client.share_file(first_client_file.name)
        time.sleep(1)  # wait a bit so that the server will update its DB
        res = second_client.search_file(os.path.basename(first_client_file.name))
        assert len(res) == 1, "Expected to find only searched file, instead got: {0}".format(res)
        requested_file = res[0]
        # Cause the first client's share server to do nothing with new clients, in order to trigger a timeout
        first_client._file_share_server._receive_new_client = lambda *args, **kwargs: Mock()
        with closed_temporary_file() as second_client_file:
            second_client.download_file(requested_file.unique_id, second_client_file.name)
            download = second_client.list_downloads()[0]
            start_time = time.time()
            while not download.is_done() and time.time() - start_time < FileDownloader.DOWNLOAD_TIMEOUT:
                continue
            assert download.failed, "Download has not failed!"
