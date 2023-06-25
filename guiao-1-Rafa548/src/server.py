"""CD Chat server program."""
import logging
import socket
import selectors
import sys
import json

from .protocol import CDProto, CDProtoBadFormat

logging.basicConfig(filename="server.log", level=logging.DEBUG)

class Server:
    """Chat Server process."""

    clients = {}

    channels = {}

    def __init__(self):
        self.sv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.sv_socket.bind(('', 1888))
        self.sv_socket.listen(2) # apenas 2 clientes de cada vez
        self.selct = selectors.DefaultSelector()
        self.selct.register(self.sv_socket, selectors.EVENT_READ, self.accept)
    
    def accept(self,socket,mask):
        conn, addr = socket.accept() # Should be ready
        
        msg = CDProto.recv_msg(conn)
        username = (msg.__dict__()).get("user")
        channel = "default"
        print("Connected user-> {} at {}".format(username,addr))
        print("User {} joined channel {}".format(username,channel))
        self.clients[conn]={"username":username,"channel":channel}
        if channel not in self.channels:
            self.channels[channel] = {}
        self.channels[channel][conn] = {"username":username}
        self.selct.register(conn, selectors.EVENT_READ, self.read)
        

    def read(self,conn,mask):
        try:
            data = CDProto.recv_msg(conn)
            if not data:
                raise ConnectionError
            if data:
                if (data.__dict__()).get("command") == "join":
                    channel = (data.__dict__()).get("channel")
                    if channel not in self.channels:
                        self.channels[channel] = {}
                    self.channels[channel][conn] = {"username":self.clients[conn]["username"]}
                    self.clients[conn]["channel"] = channel
                    print("User {} joined channel {}".format(self.clients[conn]["username"],channel))
                else:
                    username = self.clients[conn]["username"]
                    channel = self.clients[conn]["channel"]
                    logging.info("{}-{}: {}".format(username,channel,data))
                    print("{}-{}: {}".format(username,channel,(data.__dict__()).get("message")))
                    for client,c_data in self.channels[channel].items():
                        c_name = c_data["username"]
                        msg = CDProto.message((data.__dict__()).get("message"),channel)
                        CDProto.send_msg(client,msg)
                        print("Sending message to {}-{}: {}".format(c_name,channel,(data.__dict__()).get("message")))
        except Exception as e:
            print("User {} Disconnected".format(self.clients[conn]["username"]))
            channel = self.clients[conn]["channel"]
            if channel:
                del self.channels[channel][conn]
            if not self.channels[channel]:
                del self.channels[channel]
            del self.clients[conn]
            self.selct.unregister(conn)
            conn.close()
        
            
    def loop(self):
        """Loop indefinetely."""
        while True:
            events = self.selct.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
                

