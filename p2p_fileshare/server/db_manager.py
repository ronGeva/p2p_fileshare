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


def db_func(func):
    def wrapper(instance, *args, **kwargs):
        instance.lock.acquire()
        with db_cursor(instance.db_path) as cursor:
            func_res = func(instance, cursor, *args, **kwargs)
        instance.lock.release()
        return func_res
    return wrapper


class DBManager(object):
    # TODO: patch sql injections all over this class
    DEFAULT_DB_PATH = "server_db.db"

    def __init__(self, db_path=None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        if not exists(self.db_path):
            self.__create_empty_db(self.db_path)
        else:
            assert isfile(self.db_path), "Fatal error: DB path is a directory!"
        self.lock = FileLock("{prefix}.lock".format(prefix=self.db_path))

    @staticmethod
    def __create_empty_db(path):
        with db_cursor(path) as cursor:
            cursor.execute("CREATE TABLE files (file_name text, modification_time integer, size integer, origins text);")
            cursor.execute("CREATE TABLE origins (ip text, port integer);")

    @db_func
    def search_file(self, cursor: sqlite3.Cursor, filename: str):
        cursor.execute("SELECT * FROM files where file_name like '%{}%';".format(filename))
        result = cursor.fetchall()
        # TODO: get unique ID properly
        return [SharedFile(None, line[0], line[1], line[2], []) for line in result]

    @db_func
    def new_share(self, cursor: sqlite3.Cursor, new_file: SharedFile):
        cursor.execute("INSERT INTO files values ('{file_name}', {mod_time}, {size}, '{origins}');".format(
            file_name=new_file.name, mod_time=new_file.modification_time, size=new_file.size, origins=new_file.origins
        ))

    @db_func
    def remove_share(self, cursor: sqlite3.Cursor, removed_file: SharedFile, origin: FileOrigin):
        # TODO: implement remove_share
        pass
