"""Middleware to communicate with PubSub Message Broker."""
from collections.abc import Callable
from enum import Enum
from queue import LifoQueue, Empty
from typing import Any

import socket
import json
import pickle
import selectors
import xml.etree.ElementTree as ET


from .protocol import CDProto, CDProtoBadFormat



class MiddlewareType(Enum):
    """Middleware Type."""

    CONSUMER = 1
    PRODUCER = 2


class Queue:
    """Representation of Queue interface for both Consumers and Producers."""

    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        """Create Queue."""
        self.topic = topic
        self.type = _type
        self._queue = LifoQueue()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #self.selct = selectors.DefaultSelector()
        #self.selct.register(self._socket, selectors.EVENT_READ, self.pull)

        self._socket.connect(("localhost", 5000))

    #-------------------------#
    
    def decode_message(self, message):
        """Decode message from bytes to string."""
        pass 

    def encode_message(self, message):
        """Encode message from string to bytes."""
        pass

    def make_message(self,function, topic="", value=""):
        """Make message to send."""
        pass

    #--------------------------#

    def push(self, value):
        """Sends data to broker."""
        
        msg = self.make_message("publish",self.topic,str(value))
        #print(msg)
        self.send_message(msg)
        
        
    def pull(self):
        """Receives (topic, data) from broker.

        Should BLOCK the consumer!"""
        #self.subscribe(self.topic)
        
        msg_size = int.from_bytes(self._socket.recv(2), "big")
        raw_msg = self.decode_message(self._socket.recv(msg_size))
        #print(raw_msg)
        #print("hello")
        if msg_size:
            if raw_msg:
                function = raw_msg.get("function")
                if function == "p_reply":
                    topic = raw_msg.get("topic")
                    value = raw_msg.get("value")
                    #print(topic,value)
                    return topic,value    
            
    def list_topics(self, callback: Callable):
        """Lists all topics available in the broker."""
        msg = self.make_message("list")
        self.send_message(msg)
        #print(msg)

    def subscribe(self,topic):
        """Subscribe to topic."""
        message = self.make_message("subscribe",topic)
        self.send_message(message)

    def cancel(self):
        """Cancel subscription."""
        message = self.make_message("unsubscribe",self.topic)
        self.send_message(message)

    def send_message(self, message: str, type_info = False):
        """Send message to broker."""
        
        if type_info:
            message = message.encode("utf-8")
            #print(message)
        else:
            #print(message)
            message = self.encode_message(message)

        try:
            msg_size = len(message)
            msg_size = msg_size.to_bytes(length = 2,byteorder = "big")
            self._socket.send(msg_size)
            #print(message)
            #print(self.decode_message(message))
            self._socket.send(message)
        except:
            breakpoint()
     

class JSONQueue(Queue):
    """Queue implementation with JSON based serialization."""
    
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
            """Create Queue."""
            super().__init__(topic, _type)
            self.send_message("json",True)
            if self.type == MiddlewareType.CONSUMER:
                self.subscribe(self.topic)

    def decode_message(self, message):
        """Decode message from bytes to string."""
        return json.loads(message.decode("utf-8"))
    
    def encode_message(self, message):
        """Encode message from string to bytes."""
        return json.dumps(message).encode("utf-8")
    
    def make_message(self,function, topic="", value=""):
        message = {"function" : function}
        if topic:
            message["topic"] = topic
            if value:
                message["value"] = int(value)
        return message


class XMLQueue(Queue):
    """Queue implementation with XML based serialization."""

    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
            """Create Queue."""
            super().__init__(topic, _type)
            self.send_message("xml",True)
            if self.type == MiddlewareType.CONSUMER:
                self.subscribe(self.topic)

    def decode_message(self, message):
        """Decode message from bytes to string."""
        xml_tree = ET.ElementTree(ET.fromstring(message.decode("utf-8")))            
        message = {}
        for element in xml_tree.iter():
            message[element.tag] = element.text
        return message
    
    def encode_message(self, message):
        """Encode message from string to bytes."""
        return message.encode("utf-8")
    
    def make_message(self,function, topic="", value=""):
        message = "<message><function>"+function+"</function>"
        if topic:
            message = message + "<topic>"+ str(topic) +"</topic>"
            if value:
                message = message + "<value>"+ str(value) +"</value>"
        message = message + "</message>"
        return message



class PickleQueue(Queue):
    """Queue implementation with Pickle based serialization."""

    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
            """Create Queue."""
            super().__init__(topic, _type)
            self.send_message("pickle",True)
            if self.type == MiddlewareType.CONSUMER:
                self.subscribe(self.topic)

    def decode_message(self, message):
        """Decode message from bytes to string."""
        return pickle.loads(message)
    
    def encode_message(self, message):
        """Encode message from string to bytes."""
        return pickle.dumps(message)
    
    def make_message(self,function, topic="", value=""):
        message = {"function" : function}
        if topic:
            message["topic"] = topic
            if value:
                message["value"] = int(value)
        return message    
