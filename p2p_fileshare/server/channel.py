"""
A module containing the communication channel logic.
Each communication channel represents a single channel between the server and a client.
All actions in the channel must be made in a thread-safe way to ensure no data corruption is taking place.
"""
from threading import Thread
from select import select
from logging import getLogger
from db_manager import DBManager
from p2p_fileshare.framework.channel import Channel


logger = getLogger(__file__)


class ClientChannel(object):
    def __init__(self, client_channel: Channel, db: DBManager):
        self._channel = client_channel
        self._db = db
        self._closed = False
        self._thread = Thread(target=self.__start)
        self._thread.start()

    def __start(self):
        """
        This is the channel start routine which is called at its initialization and invoked as a seperated thread.
        All logic within this function must be thread safe.
        """
        while not self._closed:
            rlist, _, _ = select([self._channel], [], [], 0)
            if rlist:
                msg = self._channel.recv_message()  # TODO: make sure an entire message was received
                # TODO: perform actions with the command
                logger.debug("received message: {}".format(msg))

    def __stop(self):
        """
        Stops the channel's thread and signal the main Server component that this channel is invalid.
        """
        raise NotImplementedError