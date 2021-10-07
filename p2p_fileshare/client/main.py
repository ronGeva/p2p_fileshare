import sys
from socket import socket
from p2p_fileshare.framework.channel import Channel
from files_manager import FilesManager


COMMAND_PROMPT = """
Enter a command, one of the following:
1. search <file name or substring of it>
2. download <file ID> (id retrieved from search command)
3. share <local file path>
"""


def initialize_communication_channel(args):
    sock = socket()
    sock.connect((args[1], int(args[2]))) # TODO: validate args
    return Channel(sock)


def perform_command(user_input: str, files_manager: FilesManager):
    if user_input.startswith("search "):
        filename = user_input.split(" ")[1]
        search_result = files_manager.search_file(filename)
        for file in search_result:
            print("Name: {name}, modification time: {mod_time}, size: {size}".format(
                name=file.name, mod_time=file.modification_time, size=file.size))
    elif user_input.startswith("download "):
        unique_id = user_input.split(" ")[1]
        files_manager.download_file(unique_id)
    elif user_input.startswith("share "):
        file_path = user_input.split(" ")[1]
        files_manager.share_file(file_path)
        # TODO: allow this call to raise exceptions, if they're not fatal catch them here and print them nicely


def main(args):
    # TODO: optionally start GUI
    communication_channel = initialize_communication_channel(args)
    files_manager = FilesManager(communication_channel)
    while True:
        perform_command(input(COMMAND_PROMPT), files_manager)


if __name__ == '__main__':
    main(sys.argv)
