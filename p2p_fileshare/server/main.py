import sys
import socket
import logging
from server import MetadataServer


def main(args):
    # TODO: parse args
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)  # TODO: make this configurable
    server = MetadataServer(port=1337)
    server.main_loop()


if __name__ == '__main__':
    main(sys.argv)
