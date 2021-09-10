import sys
import socket
from server import Server


def main(args):
    # TODO: parse args
    server = Server()
    while True:
        server.main_loop()


if __name__ == '__main__':
    main(sys.argv)
