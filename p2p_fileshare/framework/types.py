"""
A module containing different types used by the application
"""
# TODO: consider using NamedTuple for this


class FileOrigin(object):
    def __init__(self, address: (str, int)):
        self.address = address
        # TODO: consider adding RTT - what does it mean for the server though?


class SharedFile(object):
    def __init__(self, unique_id: str, name: str, size: int, origins: list):
        self._unique_id = unique_id
        self._name = name
        self._size = size
        self._origins = origins
        self._downloaded_bytes = 0

    @property
    def download_state(self):
        return self._downloaded_bytes / self._size
