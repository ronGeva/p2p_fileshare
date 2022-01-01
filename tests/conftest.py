import os
import socket
from pytest import fixture
from random import randint
from os import unlink
from contextlib import contextmanager
from p2p_fileshare.server.server import MetadataServer
from p2p_fileshare.client.main import initialize_files_manager, client_id_path
from p2p_fileshare.client.files_manager import FilesManager
from p2p_fileshare.framework.channel import Channel


DEFAULT_PORT = '1337'
LOCAL_HOST = '127.0.0.1'
FIRST_USERNAME = 'first_username'
SECOND_USERNAME = 'second_username'


def generate_random_name(size: int):
    low_bound = ord('A')
    high_bound = ord('Z')
    return "".join([chr(randint(low_bound, high_bound)) for _ in range(size)])


@fixture(scope='session')
def metadata_server() -> MetadataServer:
    """
    Creates a MetadataServer with an empty db.
    On teardown the server will be properly stopped and its DB will be deleted.
    """
    random_db_name = generate_random_name(5)
    from threading import Thread
    server = MetadataServer(int(DEFAULT_PORT), db_path=random_db_name)
    server_thread = Thread(target=server.main_loop)
    server_thread.start()
    try:
        yield server
    finally:
        server.stop()
        server_thread.join(2)  # wait 2 seconds for the server to close nicely
        unlink(random_db_name)  # cleanup our DB


@contextmanager
def client(username: str) -> FilesManager:
    """
    Creates a FilesManager object with an underlying client channel.
    :param username: The username to be used for the client this FilesManager represents.
    """
    try:
        command_line = [None, LOCAL_HOST, DEFAULT_PORT, username]
        files_manager = initialize_files_manager(command_line)
        yield files_manager
    finally:
        db_path = FilesManager.generate_db_path(username)
        os.unlink(db_path)
        os.unlink(client_id_path(username))


@fixture(scope='function')
def first_client():
    with client(FIRST_USERNAME) as c:
        yield c


@fixture(scope='function')
def second_client():
    with client(SECOND_USERNAME) as c:
        yield c


@fixture(scope='function')
def server_socket():
    s = socket.socket()
    try:
        s.bind((LOCAL_HOST, 0))
        s.listen(1)
        yield s
    finally:
        s.close()


@fixture(scope='function')
def client_socket():
    s = socket.socket()
    try:
        yield s
    finally:
        s.close()


@fixture(scope='function')
def client_and_server_channels(client_socket, server_socket) -> (Channel, Channel):
    """
    Creates and return a Channel pair. The first object returned is the channel whose underlying socket is the client,
    and second object returned is the Channel whose underlying socket is the server.
    On teardown both channels will be closed.
    """
    client_socket.connect((LOCAL_HOST, server_socket.getsockname()[1]))
    server_new_socket = server_socket.accept()[0]
    client_channel = Channel(client_socket)
    server_channel = Channel(server_new_socket)
    try:
        yield client_channel, server_channel
    finally:
        client_channel.close()
        server_channel.close()


@fixture(scope='function')
def channel_pair(client_and_server_channels, request) -> (Channel, Channel):
    """
    Return a Channel pair, order of the pair is determined via indirect parametrization (to determine which of the two
    channels will be provided as the first returned object - the client or the server).
    """
    client_channel, server_channel = client_and_server_channels
    if request.param == 'client':
        return client_channel, server_channel
    else:
        return server_channel, client_channel
