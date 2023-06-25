"""Protocol for chat server - Computação Distribuida Assignment 1."""
import json
from datetime import datetime
from socket import socket

class Message:
    """Message Type."""
    
    def __init__(self,command):
        self.command = command
    
    
class JoinMessage(Message):
    """Message to join a chat channel."""
    def __init__(self,channel):
        super().__init__("join")
        self.channel = channel
        self.data = {"command": "join", "channel": self.channel}

    def __dict__(self):
        return self.data
    
    def __str__(self):
        return json.dumps(self.data)
        
    


class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self,username):
        super().__init__("register")
        self.username = username
        self.data = {"command": "register", "user": self.username}
    
    def __dict__(self):
        return self.data

    def __str__(self):
        return json.dumps(self.data)


    
class TextMessage(Message):
    """Message to chat with other clients."""
    def __init__(self, message, channel, timestamp):
        super().__init__("message")
        self.message = message
        self.timestamp = timestamp
        if channel != None:
            self.channel = channel
            self.data = {"command": "message","message": self.message,"channel": self.channel, "ts": self.timestamp}
        else:
            self.data = {"command": "message","message": self.message, "ts": self.timestamp}

    def __dict__(self):
        return self.data
        
    def __str__(self):
        return json.dumps(self.data)


class CDProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def register(cls, username: str) -> RegisterMessage:
        """Creates a RegisterMessage object."""
        msg = RegisterMessage(username)
        return msg.__str__()
        

    @classmethod
    def join(cls, channel: str) -> JoinMessage:
        """Creates a JoinMessage object."""
        msg = JoinMessage(channel)
        return msg.__str__()


    @classmethod
    def message(cls, message: str, channel: str = None) -> TextMessage:
        """Creates a TextMessage object."""
        now = datetime.now()
        epoch = datetime.utcfromtimestamp(0)
        seconds_since_epoch = (now - epoch).total_seconds()
        unix_timestamp = int(seconds_since_epoch)
        msg = TextMessage(message, channel, unix_timestamp)
        return msg.__str__()

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        """Sends through a connection a Message object."""
        msg_size = len(str(msg).encode())
        msg_size = msg_size.to_bytes(length = 2,byteorder = "big")
        connection.send(msg_size)
        connection.send(str(msg).encode())

    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        """Receives through a connection a Message object."""
        try :
            msg_size = int.from_bytes(connection.recv(2), "big")
            raw_msg = connection.recv(msg_size)
            if raw_msg != b'':
                decoded_msg = raw_msg.decode()
                json_msg = json.loads(decoded_msg)
                command = json_msg.get("command")
                if command == "register":
                    return RegisterMessage(json_msg["user"])
                elif command == "join":
                    return JoinMessage(json_msg["channel"])
                elif command == "message":
                    if json_msg.get("channel") == None:
                        return TextMessage(json_msg["message"], None, json_msg["ts"])
                    else:
                        return TextMessage(json_msg["message"], json_msg["channel"], json_msg["ts"])
        except json.decoder.JSONDecodeError:
            raise CDProtoBadFormat(raw_msg)

        
        


class CDProtoBadFormat(Exception):
    """Exception when source message is not CDProto."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self.original_msg.decode()

        
        
