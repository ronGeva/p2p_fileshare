"""
A module containing different types used by the application
"""
# TODO: consider using NamedTuple for this


class FileOrigin(object):
    def __init__(self, address: (str, int)):
        self.address = address
        # TODO: consider adding RTT - what does it mean for the server though?


class SharedFile(object):
    def __init__(self, unique_id: str, name: str, modification_time: int, size: int, origins: list):
        self.unique_id = unique_id
        self.name = name
        self.modification_time = modification_time
        self.size = size
        self.origins = origins
        self.downloaded_bytes = 0

    @property
    def download_state(self):
        return self.downloaded_bytes / self.size
