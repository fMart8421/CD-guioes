'''
Mensagem de Subscrição de um tópico
Mensagem de Publicação num tópico
Mensagem de Pedido de Listagem de tópicos
Mensagem de Cancelamento de Subscrição de um tópico
'''
import json
import pickle
from typing import List
from xml.etree.ElementTree import Element, tostring
import socket

from .enums import Serializer 
from collections import defaultdict


''' 


'''

def dict_to_xml(tag, d):
  
    elem = Element(tag)
    for key, val in d.items():
        # create an Element
        # class object
        child = Element(key)
        child.text = str(val)
        elem.append(child)
          
    return elem



def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d



class Message:
    """Message Type."""
    def __init__(self, command):
        self.command = command
    def get_dict(self):
        client_msg = {
        "command": self.command
        }
        return client_msg


class SubscribeMessage(Message):
    """Message to subscribe to a topic."""
    def __init__(self, command, topic):
        super().__init__(command)
        self.topic = topic

    def get_dict(self):
        client_msg = super().get_dict()
        client_msg["topic"] = self.topic
        return client_msg

class UnsubscribeMessage(Message):
    """Message to unsubscribe a topic."""
    def __init__(self, command, topic):
        super().__init__(command)
        self.topic = topic

    def get_dict(self):
        client_msg = super().get_dict()
        client_msg["topic"] = self.topic
        return client_msg

class ListTopics(Message):
    def __init__(self, command ):
       super().__init__(command)
        

class ListResponseMessage(Message):
    def __init__(self, command, topiclist: List[str]):
        super().__init__(command)
        self.topiclist = topiclist
    def get_dict(self):
        client_msg = super().get_dict()
        client_msg["list"] = self.topiclist

class PublishMessage(Message):
    """Message to chat with other clients."""
    def __init__(self, command, msg, topic):
        super().__init__(command)
        self.content = msg
        self.topic = topic
        
    def get_dict(self):
        client_msg = super().get_dict()
        client_msg["content"]= self.content
        client_msg["topic"] = self.topic
        return client_msg


class PubSub:
    """Computação Distribuida Protocol."""

    @classmethod
    def subscribe(cls, topic: str) -> SubscribeMessage:
        """Creates a JoinMessage object."""
        c = SubscribeMessage("subscribe", topic)
        return c

   
    @classmethod
    def unsubscribe(cls, topic: str) -> UnsubscribeMessage:
        """Creates a JoinMessage object."""
        c = UnsubscribeMessage("unsubscribe", topic)
        return c

    @classmethod
    def listTopics(cls) -> SubscribeMessage:
        """Creates a JoinMessage object."""
        c = SubscribeMessage("list")
        return c
   
    def listResponse(cls , topiclist: List[str]) -> ListResponseMessage:
        """Creates ListResponseMessage object"""
        c = ListResponseMessage("topiclist",topiclist )
        return c

    @classmethod
    def publish(cls, message: str, topic: str) -> PublishMessage:
        """Creates a TextMessage object."""
        c = PublishMessage("publish", message, topic)
        return c

    
    
    @classmethod
    def recv_msg(cls, connection: socket, serialization=Serializer.PICKLE) -> Message:
            """Receives through a connection a Message object."""
            msg_header = connection.recv(2)
            msg_len = int.from_bytes(msg_header, "big")
            if not msg_len:
                return None
            received_msg = connection.recv(msg_len)
            if serialization != Serializer.XML:   
                decoder = pickle
                if serialization == Serializer.JSON:
                    decoder=json
                    received_msg = received_msg.decode('utf-8')

                decoded_msg = decoder.loads(received_msg)
            else:
                decoded_msg = etree_to_dict(received_msg)

            if(decoded_msg["command"]=="subscribe"):
                msg = PubSub.subscribe(decoded_msg["topic"])
            elif(decoded_msg["command"]=="unsubscribe"):
                msg = PubSub.unsubscribe(decoded_msg["topic"])
            elif(decoded_msg["command"]=="publish"):
                msg = PubSub.publish(decoded_msg["content"], decoded_msg["topic"])
            return msg

    @classmethod
    def send_msg(cls, connection: socket, msg: Message, serialization):
        """Sends through a connection a Message object."""
        if serialization == Serializer.XML:
                print()
        elif serialization == Serializer.JSON:
                decoder=json
        elif serialization == Serializer.PICKLE:
                decoder = pickle
        encoded_msg = decoder.dumps(msg.get_dict())
        msg_len = len(encoded_msg)
        msg_len = msg_len.to_bytes(2,"big")
        connection.send(msg_len + encoded_msg.encode('utf-8'))

