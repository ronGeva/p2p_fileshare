from p2p_fileshare.framework.messages import *
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


def is_builtin(obj):
    return obj.__class__.__module__ == 'builtins'


def assert_objects_have_same_attributes(first, second):
    """
    Make sure both objects passed to this function have the same attributes set, and that each one of their attributes
    have equal value.
    If one of the object's attributes is of non builtin type we cannot assume it has a valid __eq__ method and we'll
    resort to using this function recursively on it.
    """
    assert isinstance(first, type(second)), "Objects have different type!"
    assert set(first.__dict__) == set(second.__dict__), "Objects have non matching attributes set"
    for attr in first.__dict__:
        first_attr = getattr(first, attr)
        second_attr = getattr(second, attr)
        if is_builtin(first_attr):
            assert first_attr == second_attr
        else:
            assert_objects_have_same_attributes(first_attr, second_attr)


@pytest.mark.parametrize('message', MESSAGES)
def test_message_serialization(message):
    """
    This test asserts serializing and then deserializing a message results in a message containing identical data,
    which means the message's serialization logic works as intended.
    """
    after_serialization_message = Message.deserialize(message.serialize())
    assert_objects_have_same_attributes(message, after_serialization_message)
