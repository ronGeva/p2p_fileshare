import sys
import socket
import logging
from server import Server


def main(args):
    # TODO: parse args
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    server = Server()
    while True:
        server.main_loop()


if __name__ == '__main__':
    main(sys.argv)
