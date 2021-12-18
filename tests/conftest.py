from pytest import fixture
from multiprocessing import Process
from random import randint
from os import unlink
from p2p_fileshare.server.server import MetadataServer
from p2p_fileshare.client.main import initialize_files_manager


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
    server = MetadataServer(int(DEFAULT_PORT), db_path=random_db_name)
    server_process = Process(target=server.main_loop)
    server_process.start()
    try:
        yield server
    finally:
        server_process.terminate()
        unlink(random_db_name)  # cleanup our DB


@fixture(scope='function')
def client():
    command_line = [None, LOCAL_HOST, DEFAULT_PORT, FIRST_USERNAME]
    files_manager = initialize_files_manager(command_line)
    return files_manager


@fixture(scope='function')
def another_client():
    command_line = [None, LOCAL_HOST, DEFAULT_PORT, SECOND_USERNAME]
    files_manager = initialize_files_manager(command_line)
    return files_manager
