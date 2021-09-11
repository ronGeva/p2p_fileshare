"""
This modules governs DB-related actions.
"""
from p2p_fileshare.framework.types import SharedFile, FileOrigin


class DBManager(object):
    def __init__(self, db_path=None):
        pass

    def search_file(self, filename: str):
        pass

    def new_share(self, new_file: SharedFile, origin: FileOrigin):
        pass

    def remove_share(self, removed_file: SharedFile, origin: FileOrigin):
        pass
