"""
This modules governs DB-related actions.
"""
import logging
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from filelock import FileLock
from os.path import exists, isfile
from p2p_fileshare.framework.types import SharedFile, FileOrigin


DB_LOCK_TIMEOUT = 10


@contextmanager
def db_cursor(path: str) -> sqlite3.Cursor:
    """
    This function yields a DB cursor to the sqlite db whose file is located at path.
    """
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    yield cursor
    conn.commit()
    conn.close()


def db_func(func):
    """
    A decorator wrapping a DBManager method so that its second parameter (after self) will be a cursor to its DB.
    This function is thread safe via file locks.
    """
    def db_func_wrapper(instance, *args, **kwargs):
        lock = FileLock(instance.lock_path)
        try:
            lock.acquire(timeout=DB_LOCK_TIMEOUT)
            with db_cursor(instance.db_path) as cursor:
                func_res = func(instance, cursor, *args, **kwargs)
            return func_res
        finally:
            lock.release()  # lock must be freed even if the function failed
    return db_func_wrapper


class AbstractDBManager(ABC):
    # TODO: patch sql injections all over this class
    DEFAULT_DB_PATH = "server_db.db"

    def __init__(self, db_path=None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        if not exists(self.db_path):
            self.create_empty_db()
        else:
            assert isfile(self.db_path), "Fatal error: DB path is a directory!"
        self.lock_path = f"{self.db_path}.lock"

    def create_empty_db(self):
        with db_cursor(self.db_path) as cursor:
            self._create_empty_db(cursor)

    @abstractmethod
    def _create_empty_db(self, cursor):
        """
        Initializes the DB with the required tables for the application to function properly.
        """
        pass
