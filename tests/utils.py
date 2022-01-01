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
