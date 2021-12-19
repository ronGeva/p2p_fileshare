import os

from pytest import fixture
from random import randint
from os import unlink
from contextlib import contextmanager
from p2p_fileshare.server.server import MetadataServer
from p2p_fileshare.client.main import initialize_files_manager
from p2p_fileshare.client.files_manager import FilesManager


DEFAULT_PORT = '1337'
LOCAL_HOST = '127.0.0.1'
FIRST_USERNAME = 'first_username'
SECOND_USERNAME = 'second_username'


def generate_random_name(size: int):
    low_bound = ord('A')
    high_bound = ord('Z')
    return "".join([chr(randint(low_bound, high_bound)) for _ in range(size)])


@fixture(scope='session')
def metadata_server():
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
    try:
        command_line = [None, LOCAL_HOST, DEFAULT_PORT, username]
        files_manager = initialize_files_manager(command_line)
        yield files_manager
    finally:
        db_path = FilesManager.generate_db_path(username)
        os.unlink(db_path)


@fixture(scope='module')
def first_client():
    with client(FIRST_USERNAME) as c:
        yield c


@fixture(scope='module')
def second_client():
    with client(SECOND_USERNAME) as c:
        yield c
