"""
This module governs the client-side database actions, mainly keeping the state of the application between runs (so
that the client would be aware of files he's currently sharing).
"""
import sqlite3

from p2p_fileshare.framework.db import AbstractDBManager, db_func


class DBManager(AbstractDBManager):
    DEFAULT_DB_PATH = "client_db.db"

    def _create_empty_db(self, cursor):
        cursor.execute("CREATE TABLE files (file_path text, unique_id text, PRIMARY KEY('unique_id'));")

    @db_func
    def get_shared_file_path(self, cursor: sqlite3.Cursor, unique_id: str):
        cursor.execute("select path from files where unique_id='{unique_id}'".format(unique_id=unique_id))
        result = cursor.fetchall()
        if len(result) == 0:
            return None
        return result[0]

    @db_func
    def is_there_any_shared_file(self, cursor: sqlite3.Cursor):
        cursor.execute("select * from files")
        return len(cursor.fetchall()) > 0

    @db_func
    def add_share(self, cursor: sqlite3.Cursor, unique_id: str, file_path: str):
        cursor.execute("insert into files values ('{file_path}', '{unique_id}')".format(
            file_path=file_path, unique_id=unique_id))