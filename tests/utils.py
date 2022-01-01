import logging


class LogStashHandler(logging.Handler):
    """
    This class implements the minimal requirements of a logging handler.
    The handle method of this class simply appends the record into a list of logs, to be viewed later by tests.
    """
    def __init__(self, *args, **kwargs):
        super(LogStashHandler, self).__init__(*args, **kwargs)
        self.logs = []
        self.level = logging.DEBUG  # get ALL logs

    def handle(self, record: logging.LogRecord):
        self.logs.append(record)
        return record


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