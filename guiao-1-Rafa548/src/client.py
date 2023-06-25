"""CD Chat client program"""
import logging
import sys
import socket
import fcntl
import os
import selectors
import json
import datetime

from .protocol import CDProto, CDProtoBadFormat

logging.basicConfig(filename=f"{sys.argv[0]}.log", level=logging.DEBUG)

class Client:
    """Chat Client process."""

    selct = None
    client_socket = None
    u_name = None
    channel_name = "default"

    orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

    def __init__(self,name: str = "Foo" ):
        
        self.channel_name = "default"
        self.u_name = name

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = client_socket

        selct = selectors.DefaultSelector()
        selct.register(self.client_socket, selectors.EVENT_READ, Client.read)
        selct.register(sys.stdin, selectors.EVENT_READ, Client.keyboard_data)
        self.selct = selct


    def keyboard_data(socket,stdin):
        """Read data from stdin and send it to the server."""
        
        input = stdin.read().strip()
        args = input.split()

        if len(args) != 0 and args[0] == "/join":
            msg = CDProto.join(args[1])
            Client.channel_name = args[1]
            CDProto.send_msg(socket,msg)
        else:
            if Client.u_name != '':
                msg = CDProto.message(input,Client.channel_name)
                CDProto.send_msg(socket,msg)


    def connect(self):
        """Connect to chat server and setup stdin flags."""
        self.client_socket.connect(('', 1888))
        msg = CDProto.register(self.u_name)
        CDProto.send_msg(self.client_socket,msg)
        
    def read(socket,stdin):
        data = CDProto.recv_msg(socket)
        if data:
            channel = (data.__dict__()).get("channel")
            msg = "{}: {}".format(channel,(data.__dict__()).get("message"))
            print(msg)
        

    def loop(self):
        """Loop indefinetely."""
        while True:
            events = self.selct.select()
            for key, mask in events:
                callback = key.data
                callback(self.client_socket, sys.stdin)
