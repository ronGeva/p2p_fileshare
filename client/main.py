import sys
from channel import Channel
from files_manager import FilesManager


def initialize_communication_channel(args):
    return Channel((args[1], int(args[2])))


def main(args):
    # TODO: optionally start GUI
    communication_channel = initialize_communication_channel(args)
    files_manager = FilesManager(communication_channel)
    while True:
        pass  # TODO: implement a way for the user to insert commands to the files manager


if __name__ == '__main__':
    main(sys.argv)
