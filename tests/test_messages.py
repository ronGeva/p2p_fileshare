from p2p_fileshare.framework.messages import *
from utils import assert_objects_have_same_attributes
import pytest


DUMMY_UNIQUE_ID = 'a' * 32
DUMMY_NAME = 'myFile.txt'
DUMMY_MODIFICATION_TIME = 100
DUMMY_SIZE = 5 * 1024 * 1024  # 5 MB
DUMMY_ORIGINS = []
DUMMY_SHARED_FILE = SharedFile(DUMMY_UNIQUE_ID, DUMMY_NAME, DUMMY_MODIFICATION_TIME, DUMMY_SIZE, DUMMY_ORIGINS)
DUMMY_CHUNK_NUM = 15
DUMMY_DATA = b"A" * 1024
DUMMY_MESSAGE = "This is a message"
DUMMY_PORT = 8080

MESSAGES = [
    SearchFileMessage(DUMMY_NAME),
    ShareFileMessage(DUMMY_SHARED_FILE),
    ClientIdMessage(DUMMY_UNIQUE_ID),
    SharingInfoRequestMessage(DUMMY_UNIQUE_ID),
    SharingInfoResponseMessage(DUMMY_SHARED_FILE),
    StartFileTransferMessage(DUMMY_UNIQUE_ID, DUMMY_CHUNK_NUM),
    ChunkDataResponseMessage(DUMMY_UNIQUE_ID, DUMMY_CHUNK_NUM, DUMMY_DATA),
    GeneralSuccessMessage(DUMMY_MESSAGE),
    GeneralErrorMessage(DUMMY_MESSAGE),
    RemoveShareMessage(DUMMY_UNIQUE_ID),
    SharePortMessage(DUMMY_PORT)
]


@pytest.mark.parametrize('message', MESSAGES, ids=[type(message).__name__ for message in MESSAGES])
def test_message_serialization(message):
    """
    This test asserts serializing and then deserializing a message results in a message containing identical data,
    which means the message's serialization logic works as intended.
    """
    after_serialization_message = Message.deserialize(message.serialize())
    assert_objects_have_same_attributes(message, after_serialization_message)
