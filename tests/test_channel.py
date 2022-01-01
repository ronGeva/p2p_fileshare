from p2p_fileshare.framework.messages import SearchFileMessage, ClientIdMessage
from p2p_fileshare.framework.channel import Channel, TimeoutException
from utils import assert_objects_have_same_attributes
import pytest


DUMMY_MSG = SearchFileMessage('myFile')


@pytest.mark.parametrize('channel_pair', ['client', 'server'], indirect=True)
def test_channel_simple_message(channel_pair: (Channel, Channel)):
    """
    Send a message between two channels and asserts it is received properly.
    """
    sender, receiver = channel_pair
    sender.send_message(DUMMY_MSG)
    received_msg = receiver.recv_message(1)
    assert_objects_have_same_attributes(DUMMY_MSG, received_msg)


@pytest.mark.parametrize('channel_pair', ['client', 'server'], indirect=True)
def test_channel_timeout_no_msg(channel_pair: (Channel, Channel)):
    """
    Attempt to receive a message when non has been sent and expect a TimeoutException.
    """
    sender, receiver = channel_pair
    with pytest.raises(TimeoutException):
        receiver.recv_message(1)


@pytest.mark.parametrize('channel_pair', ['client', 'server'], indirect=True)
def test_channel_timeout_wrong_message(channel_pair: (Channel, Channel)):
    """
    Attempt to receive a message from a specific type while the sender only sent a different type of message.
    We expect a TimeoutException to be raised.
    """
    sender, receiver = channel_pair
    sender.send_message(DUMMY_MSG)
    with pytest.raises(TimeoutException):
        receiver.wait_for_message(ClientIdMessage, 1)
