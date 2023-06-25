"""Protocol for chat server - Computação Distribuida Assignment 1."""

import json
from datetime import datetime
from socket import socket

class Message:
    """Message Type."""
    
    def __init__(self,command):
        self.command = command

class PublishMessage(Message):
    """Message to join a topic channel."""
    def __init__(self,topic,message):
        super().__init__("publish")
        self.topic = topic
        self.message = message
        self.data = {"command": "publish", "topic": self.topic, "message": self.message}

    def __dict__(self):
        return self.data
    
    def __str__(self):
        return json.dumps(self.data)
    
class NewTopicEntry(Message):
    """Message to send to topic channel."""
    def __init__(self,topic,message):
        super().__init__("new_topic_entry")
        self.topic = topic
        self.message = message
        self.data = {"command": "new_topic_entry","topic": self.topic , "message": self.message}

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
    
class SubscribeMessage(Message):
    """Message to join a topic channel."""
    def __init__(self,topic):
        super().__init__("subscribe")
        self.topic = topic
        self.data = {"command": "subscribe", "topic": self.topic, "format": "json"}

    def __dict__(self):
        return self.data
    
    def __str__(self):
        return json.dumps(self.data)
    
class UnsubscribeMessage(Message):
    """Message to join a topic channel."""
    def __init__(self,topic):
        super().__init__("unsubscribe")
        self.channel = topic
        self.data = {"command": "unsubscribe", "topic": self.topic}

    def __dict__(self):
        return self.data
    
    def __str__(self):
        return json.dumps(self.data)


class ListTopics(Message):
    def __init__(self):
        super().__init__("list_topics")
        self.data = {"command": "list_topics"}

    def __dict__(self):
        return self.data
    
    def __str__(self):
        return json.dumps(self.data)

class ReturnTopics(Message):
    def __init__(self,message):
        super().__init__("topics")
        self.message = message
        self.data = {"command": "topics", "topics": self.message}
    
    def __dict__(self):
        return self.data
    
    def __str__(self):
        return json.dumps(self.data)
    
class TextMessage(Message):
    """Message to share with other clients."""
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
    def subscribe(cls, topic: str):
        """Creates a SubscribeMessage object."""
        msg = SubscribeMessage(topic)
        return msg.__str__()
    
    @classmethod
    def unsubscribe(cls, topic: str):
        """Creates a UnsubscribeMessage object."""
        msg = UnsubscribeMessage(topic)
        return msg.__str__()

    @classmethod
    def list_topics(cls):
        """Creates a list_topicsMessage object."""
        msg = ListTopics()
        return msg.__str__()
    
    @classmethod
    def return_topics(cls, message: str):
        """Creates a ReturnTopics object."""
        msg = ReturnTopics(message)
        return msg.__str__()
    
    @classmethod
    def publish(cls, topic: str, message: str =None):
        """Creates a PublishMessage object."""
        msg = PublishMessage(topic, message)
        return msg.__str__()
    
    @classmethod
    def new_topic_entry(cls,topic: str, message: str):
        """Creates a NewTopicEntry object."""
        msg = NewTopicEntry(topic,message)
        return msg.__str__()

    @classmethod
    def message(cls, message: str, channel: str = None):
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
    def recv_msg(cls, connection: socket):
        """Receives through a connection a Message object."""
        try :
            msg_size = int.from_bytes(connection.recv(2), "big")
            raw_msg = connection.recv(msg_size)
            if raw_msg != b'':
                decoded_msg = raw_msg.decode()
                json_msg = json.loads(decoded_msg)
                command = json_msg.get("command")
                if command == "publish":
                    return PublishMessage(json_msg["topic"], json_msg["message"])
                elif command == "subscribe":
                    return SubscribeMessage(json_msg["topic"])
                elif command == "unsubscribe":
                    return UnsubscribeMessage(json_msg["topic"])
                elif command == "list_topics":
                    return ListTopics()
                elif command == "topics":
                    return ReturnTopics(json_msg["topics"])
                elif command == "new_topic_entry":
                    return NewTopicEntry(json_msg["topic"],json_msg["message"])
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

        
        
