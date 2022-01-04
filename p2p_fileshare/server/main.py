import sys
import logging
from server import MetadataServer


def main(args):
    """
    The metadata server's start routine.
    """
    port = 1337
    if len(args) >= 2 and args[1].isdigit():
        port = int(args[1])
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    server = MetadataServer(port=port)
    server.main_loop()


if __name__ == '__main__':
    main(sys.argv)
