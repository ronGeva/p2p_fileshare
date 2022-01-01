"""
This module implements the functionality needed to generate selectable "events" that can be used to wait on both network
as well as non network operations.

This functionality is implemented by connecting a new socket to a listening socket and using the new socket pair
 as the "event provider" and "event consumer". The client side can signal the event by sending a one byte message, and
 the server side can consume the event by using select on the socket and then reading a single byte.
"""
import socket


def generate_socket_pair(listening_socket: socket.socket) -> tuple[socket.socket, socket.socket]:
    """
    Creates a socket-pair (provider + consumer) and returns them as (provider, consumer).
    """
    provider_socket = socket.socket()
    provider_socket.connect(("127.0.0.1", listening_socket.getsockname()[1]))
    consuming_socket, _ = listening_socket.accept()

    return provider_socket, consuming_socket


def signal(provider_socket: socket.socket):
    provider_socket.send(bytes(1))  # we just need to send a single byte
