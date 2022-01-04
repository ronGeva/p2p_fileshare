"""
This module governs the client-side database actions, mainly keeping the state of the application between runs (so
that the client would be aware of files he's currently sharing).
"""
import sqlite3

from p2p_fileshare.framework.db import AbstractDBManager, db_func


class DBManager(AbstractDBManager):
    """
    This class governs access to the client's db - used to hold persistent data across multiple starts of the
    application.
    """
    DEFAULT_DB_PATH = "client_db.db"

    def _create_empty_db(self, cursor):
        cursor.execute("CREATE TABLE files (file_path text, unique_id text, PRIMARY KEY('unique_id'));")

    @db_func
    def get_shared_file_path(self, cursor: sqlite3.Cursor, unique_id: str):
        cursor.execute(f"select file_path from files where unique_id='{unique_id}'")
        result = cursor.fetchall()
        if len(result) == 0:
            return None
        return result[0][0]

    @db_func
    def is_there_any_shared_file(self, cursor: sqlite3.Cursor):
        cursor.execute("select * from files")
        return len(cursor.fetchall()) > 0

    @db_func
    def add_share(self, cursor: sqlite3.Cursor, unique_id: str, file_path: str):
        cursor.execute(f"insert into files values ('{file_path}', '{unique_id}')")

    @db_func
    def list_shares(self, cursor: sqlite3.Cursor):
        cursor.execute(f"select * from files")
        return cursor.fetchall()

    def _is_file_shared(self, cursor: sqlite3.Cursor, unique_id: str) -> bool:
        cursor.execute(f"select * from files where unique_id='{unique_id}'")
        result = cursor.fetchall()
        return len(result) > 0

    @db_func
    def remove_share(self, cursor: sqlite3.Cursor, unique_id: str):
        if not self._is_file_shared(cursor, unique_id):
            raise ValueError(f"File with unique ID {unique_id} isn't shared by the client!")
        cursor.execute(f"delete from files where unique_id='{unique_id}'")
