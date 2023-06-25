"""Message Broker"""
import enum
import socket
from typing import Dict, List, Any, Tuple

import selectors
import json
import pickle
import xml.etree.ElementTree as ET

from .protocol import CDProto, CDProtoBadFormat



class Serializer(enum.Enum):
    """Possible message serializers."""

    JSON = 0
    XML = 1
    PICKLE = 2


class Broker:
    """Implementation of a PubSub Message Broker."""

    def __init__(self):
        """Initialize broker."""
        self.canceled = False
        self._host = "localhost"
        self._port = 5000

        self._socket = self.BrokerSocket(self._host, self._port)        

        #self.consumer_topics = {}
        self.topics_le = {}
        self.conn_types = {}
        self.subscriptions = {}

        self.selct = selectors.DefaultSelector()
        self.selct.register(self._socket, selectors.EVENT_READ, self.accept)

    def accept(self, sock: socket.socket,mask):
        """Reads message from socket."""
        conn, addr = sock.accept()
        #print("accepted connection from", addr)
        self.selct.register(conn, selectors.EVENT_READ, self.read)

    def list_topics(self) -> List[str]:
        """Returns a list of strings containing all topics containing values."""
        return list(self.topics_le.keys())

    def get_topic(self, topic):
        """Returns the currently stored value in topic."""
        if topic not in self.topics_le:
            return None
        return self.topics_le[topic]

    def put_topic(self, topic, value):
        """Store in topic the value."""
        self.topics_le[topic] = value

    def list_subscriptions(self, topic: str) -> List[Tuple[socket.socket, Serializer]]:
        """Provide list of subscribers to a given topic."""
        return self.subscriptions[topic]

    def subscribe(self, topic: str, addr: socket.socket, _format: Serializer = None):
        """Subscribe to topic by client in address."""
        x=0
        if topic not in self.subscriptions:
            self.subscriptions[topic] = [(addr,_format)]
        for topico,list in self.subscriptions.items():
            for tuplo in list:
                if tuplo[0] == addr:
                    x += 1
        if x == 0:
            self.subscriptions[topic].append((addr,_format))
                
        if topic in self.topics_le:
            self.send_msg(addr,topic,self.topics_le[topic])

        """ if addr not in self.consumer_topics:
            self.consumer_topics[addr] = [topic]
        elif topic not in self.consumer_topics[addr]:
            self.consumer_topics[addr].append(topic) """
        
        
        

    def unsubscribe(self, topic, addr):
        """Unsubscribe to topic by client in address."""
        """ if topic in self.consumer_topics[addr]:
            self.consumer_topics[addr].remove(topic) """
        
        if topic in self.subscriptions:
            for topico,list in self.subscriptions.items():
                if topic == topico:
                    for tuplo in list:
                        if addr == tuplo[0]:
                            list.remove(tuplo)

                
        

    def run(self):
        """Run until canceled."""

        while not self.canceled:
            events = self.selct.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    


    def send_msg(self,consumer,topic,value): 
        if self.conn_types[consumer] == "json":
            msg = {"function":"p_reply","topic":topic,"value":value}
            #print(msg)
            msg = json.dumps(msg)
            msg_size = len(msg.encode("utf-8"))
            msg_size = msg_size.to_bytes(length = 2,byteorder = "big")
            consumer.send(msg_size)
            consumer.send(msg.encode("utf-8"))
        elif self.conn_types[consumer] == "pickle":
            msg = {"function":"p_reply","topic":topic,"value":value}
            #print(msg)
            #print(msg)
            msg = pickle.dumps(msg)
            msg_size = len(msg)
            msg_size = msg_size.to_bytes(length = 2,byteorder = "big")
            consumer.send(msg_size)
            consumer.send(msg)
        elif self.conn_types[consumer] == "xml":
            msg = "<message><function>p_reply</function><topic>"+ topic +"</topic><value>"+ str(value) +"</value></message>"
            msg_size = len(msg.encode("utf-8"))
            msg_size = msg_size.to_bytes(length = 2,byteorder = "big")
            consumer.send(msg_size)
            consumer.send(msg.encode("utf-8"))


    def read(self,conn,mask):
        """Reads message from socket."""
        """ try: """
        
        msg_size = int.from_bytes(conn.recv(2), "big")
        
        #print(raw_msg.decode())
        #breakpoint()
        if msg_size:
            raw_msg = conn.recv(msg_size)
            if raw_msg:
                if conn not in self.conn_types:
                    decoded_msg = raw_msg.decode("utf-8")
                    self.conn_types[conn] = decoded_msg
                    #print(self.conn_types)
                else:
                    #print("type: "+self.conn_types[conn])
                    if self.conn_types[conn] == "json":
                        decoded_msg = raw_msg.decode("utf-8")
                        msg = json.loads(decoded_msg)
                        #print(msg)
                    elif self.conn_types[conn] == "pickle":
                        decoded_msg = raw_msg
                        msg = pickle.loads(decoded_msg)
                    elif self.conn_types[conn] == "xml":
                        decoded_msg = raw_msg.decode("utf-8")
                        xml_tree = ET.ElementTree(ET.fromstring(decoded_msg))
                        msg = {}
                        for elem in xml_tree.iter():
                            msg[elem.tag] = elem.text
                
                    #print(decoded_msg)
                    
                    #print(msg)
                    function = msg.get("function")
                    #print(function)
                    if function == "subscribe":
                        topic = msg.get("topic")
                        self.subscribe(topic,conn)
                    elif function == "unsubscribe":
                        topic = msg.get("topic")
                        if conn in self.consumer_topics:
                            self.unsubscribe(topic,conn)
                    elif function == "publish":
                        #print(msg)
                        topic = msg.get("topic")
                        #print(topic)
                        topic_array = topic.split("/")
                        #topic_array.reverse()
                        value = msg.get("value")
                        #print(topic,value)
                        self.put_topic(topic,value)
                        for topico,list in self.subscriptions.items():
                            temp = "/"
                            #print("entrou")
                            if topic == topico:
                                for tuplo in list:
                                    #print(tuplo[0])
                                    self.send_msg(tuplo[0],topic,value)
                            #breakpoint()
                            for final_topic in topic_array:
                                if final_topic != "":
                                    #print(final_topic)
                                    temp += final_topic
                                    #print(temp)
                                    if temp == topico:
                                        print("entrou")
                                        for tuplo in list:
                                            #print(tuplo[0])
                                            self.send_msg(tuplo[0],topic,value)
                                        temp += "/"
                                    else:
                                        temp += "/"        
                    elif function == "list":
                        list = self.list_topics()

        else:
            #print("closing", conn)
            del self.conn_types[conn]
            for topico,list in self.subscriptions.items():
                    for tuplo in list:
                        if conn == tuplo[0]:
                            list.remove(tuplo)
            self.selct.unregister(conn)
            conn.close()

    def BrokerSocket(self,host, port):
        """Create a socket for the broker."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        s.bind((host, port))
        s.listen()
        s.setblocking(False)
        return s
