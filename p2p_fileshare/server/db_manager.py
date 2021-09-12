"""
This modules governs DB-related actions.
"""
import sqlite3
from contextlib import contextmanager
from filelock import FileLock
from os.path import exists, isfile
from p2p_fileshare.framework.types import SharedFile, FileOrigin


@contextmanager
def db_cursor(path):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    yield cursor
    conn.commit()
    conn.close()


def thread_safe(func):
    def wrapper(instance: DBManager, *args, **kwargs):
        instance._lock.acqurie()
        return func(instance, *args, **kwargs)
    return wrapper


class DBManager(object):
    DEFAULT_DB_PATH = "server_db.db"

    def __init__(self, db_path=None):
        self._db_path = db_path or self.DEFAULT_DB_PATH
        if not exists(self._db_path):
            self.__create_empty_db(self._db_path)
        else:
            assert isfile(self._db_path), "Fatal error: DB path is a directory!"
        self._lock = FileLock("{perfix}.lock".format(prefix=self._db_path))

    @staticmethod
    def __create_empty_db(path):
        with db_cursor(path) as cursor:
            cursor.execute("CREATE TABLE files (file_name text, modification_time integer, size integer, origins text)")
            cursor.execute("CREATE TABLE origins (ip text, port integer)")

    @thread_safe
    def search_file(self, filename: str):
        pass

    @thread_safe
    def new_share(self, new_file: SharedFile, origin: FileOrigin):
        pass

    @thread_safe
    def remove_share(self, removed_file: SharedFile, origin: FileOrigin):
        pass
