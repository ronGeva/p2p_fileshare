import sys
import traceback
from socket import socket
from p2p_fileshare.framework.channel import Channel
from p2p_fileshare.framework.messages import ClientIdMessage
from files_manager import FilesManager
from os.path import abspath, dirname, join
from typing import Optional


CLIENT_ID_STORAGE = join(dirname(abspath(__file__)), 'CLIENT_ID.dat')
ID_RETRIEVAL_TIMEOUT = 60

COMMAND_PROMPT = """
Enter a command, one of the following:
1. search <file name or substring of it>
2. download <file ID> <Local path> (ID retrieved from search command)
3. share <local file path>
4. list-downloads
5. remove-download <Downloader ID> (ID retrieved from list-downloads command)
0. exit
"""


def initialize_communication_channel(args):
    sock = socket()
    server_address = (args[1], int(args[2]))
    sock.connect(server_address)  # TODO: validate args
    return Channel(sock)


def perform_command(user_input: str, files_manager: FilesManager):
    ## TODO - change ot arg parse for each option
    if user_input.startswith("search "):
        filename = user_input.split(" ")[1]
        search_result = files_manager.search_file(filename)
        for file in search_result:
            print(f"Name: {file.name}, modification time: {file.modification_time}, size: {file.size}, unqiue_id: {file.unique_id}")
    elif user_input.startswith("download "):
        unique_id, local_path = user_input.split(" ")[1:]
        files_manager.download_file(unique_id, local_path)
    elif user_input.startswith("share "):
        file_path = user_input.split(" ")[1]
        files_manager.share_file(file_path)
        # TODO: allow this call to raise exceptions, if they're not fatal catch them here and print them nicely
    elif user_input.startswith("list-downloads"):
        downloaders = files_manager.list_downloads()
        for fd_id in downloaders:
            if downloaders[fd_id].is_done():
                print(f"{fd_id}: Done")  # TODO: handle failed downloads
            else:
                print(f"{fd_id}: In progress")
    elif user_input.startswith("remove-download "):
        downloader_id = user_input.split(" ")[1]
        files_manager.remove_download(downloader_id)
    elif user_input.startswith("exit"):
        return True
    return False


def get_client_id() -> Optional[str]:
    """
    Retrieves the client's unique id from a hard-coded path.
    If the unique id is not found, returns None
    :return string representing the unique id of the client (32 characters long), or None.
    """
    try:
        with open(CLIENT_ID_STORAGE, 'r') as f:
            return f.read().strip()
    except IOError:
        return None


def resolve_id(communication_channel: Channel):
    """
    Notifies the server of our current client id, and in case it isn't initialized yet - waits until the server assigns
    us a unique id.
    :param communication_channel: The communication channel with the server.
    :return: None.
    """
    client_id = get_client_id()
    client_id_msg = ClientIdMessage(client_id)
    communication_channel.send_message(client_id_msg)  # notify the server of our current id
    if client_id is None:
        client_id_msg = communication_channel.wait_for_message(ClientIdMessage, timeout=ID_RETRIEVAL_TIMEOUT)
        with open(CLIENT_ID_STORAGE, 'w') as f:
            f.write(client_id_msg.unique_id)


def main(args):
    # TODO: optionally start GUI
    communication_channel = initialize_communication_channel(args)
    resolve_id(communication_channel)
    files_manager = FilesManager(communication_channel)
    should_exit = False
    while not should_exit:
        try:
            should_exit = perform_command(input(COMMAND_PROMPT), files_manager)
        except Exception as e:
            print('Couldn\'t perform command :(')
            print(traceback.format_exc())


if __name__ == '__main__':
    main(sys.argv)
