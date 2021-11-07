"""
This modules governs DB-related actions.
"""
import logging
import sqlite3
from contextlib import contextmanager
from p2p_fileshare.framework.types import SharedFile, FileOrigin
from p2p_fileshare.framework.db import AbstractDBManager, db_func


logger = logging.getLogger(__file__)


class DBManager(AbstractDBManager):
    def _create_empty_db(self, cursor):
        cursor.execute("CREATE TABLE files (file_name text, modification_time integer, size integer, "
                       "unique_id text, PRIMARY KEY('unique_id'));")
        cursor.execute("CREATE TABLE origins (unique_id text, PRIMARY KEY('unique_id'))")
        cursor.execute("CREATE TABLE shares (file text , origin text, PRIMARY KEY ('file', 'origin'))")

    @db_func
    def search_file(self, cursor: sqlite3.Cursor, filename: str) -> list[SharedFile]:
        """
        Searches for a single file via its filename.
        Every file containing the requested filename as a substring will be retrieved.
        :return: A list of the files (each represented by a SharedFile object).
        """
        cursor.execute("SELECT * FROM files where file_name like '%{}%';".format(filename))
        result = cursor.fetchall()
        return [SharedFile(line[3], line[0], line[1], line[2], []) for line in result]

    @staticmethod
    def _does_file_exist(cursor: sqlite3.Cursor, unique_id: str) -> int:
        cursor.execute("SELECT rowid from files where unique_id = '{unique_id}';".format(unique_id=unique_id))
        return cursor.fetchone() is not None

    @staticmethod
    def _add_new_file(cursor: sqlite3.Cursor, new_file: SharedFile):
        """
        If the new file doesn't exist in the files table, adds it.
        """
        if not DBManager._does_file_exist(cursor, new_file.unique_id):
            cursor.execute("INSERT INTO files values ('{file_name}', {mod_time}, {size}, '{unique_id}');".format(
                file_name=new_file.name, mod_time=new_file.modification_time, size=new_file.size,
                unique_id=new_file.unique_id))

    @staticmethod
    def _is_client_sharing_file(cursor: sqlite3.Cursor, file_id: str, origin_id: str):
        cursor.execute("SELECT rowid from shares where file='{file_id}' and origin='{origin_id}'".format(
            file_id=file_id, origin_id=origin_id))
        return cursor.fetchone() is not None

    @db_func
    def new_share(self, cursor: sqlite3.Cursor, new_file: SharedFile, origin_id: str):
        """
        Adds a new share to the shares table, and in case the file added isn't in the files table, adds it to it.
        :return: None.
        """
        if not self._is_client_sharing_file(cursor, new_file.unique_id, origin_id):
            self._add_new_file(cursor, new_file)
            cursor.execute("INSERT INTO shares values ('{file_id}', '{origin_id}');".format(file_id=new_file.unique_id,
                                                                                            origin_id=origin_id))
        else:
            logger.warning("A client tried to share the same file twice. Client id {0}, file id {1}".format(
                origin_id, new_file.unique_id))

    @staticmethod
    def _does_client_exist(cursor: sqlite3.Cursor, unique_id: str):
        """
        :return: Whether or not a client exist in the origins table, via its unique_id (the table's primary key).
        """
        cursor.execute("SELECT rowid from origins where unique_id = '{unique_id}'".format(unique_id=unique_id))
        return cursor.fetchone() is not None

    @db_func
    def add_new_client(self, cursor: sqlite3.Cursor, unique_id: str):
        """
        Adds a new client to the origins table.
        """
        if not self._does_client_exist(cursor, unique_id):
            cursor.execute("INSERT INTO origins values ('{unique_id}')".format(unique_id=unique_id))

    @db_func
    def remove_share(self, cursor: sqlite3.Cursor, removed_file: SharedFile, origin: FileOrigin):
        """
        Removes a single client from the sharing list of a file.
        """
        # TODO: implement remove_share
        pass

    @db_func
    def find_sharing_clients(self, cursor: sqlite3.Cursor, file_unique_id: str):
        """
        Retrieves all the clients (identified by their unique id) that share the file identified by the unique id
        supplied to this method.
        """
        cursor.execute("select origin from shares where file = '{file_unique_id}'".format(
            file_unique_id=file_unique_id))
        return [line[0] for line in cursor.fetchall()]
