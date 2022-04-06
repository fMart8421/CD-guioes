"""Middleware to communicate with PubSub Message Broker."""
import json
import pickle
import socket
from collections.abc import Callable
from queue import Empty, LifoQueue
import sys
import traceback
from typing import Any
from xml.etree.ElementTree import Element, tostring
from src.PubSub import PubSub
from .enums import MiddlewareType
from collections import defaultdict
'''
Producer faz send para o broker, este faz send para a queue do consumer
cada queue vai ser uma socket
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

class Queue:
    """Representation of Queue interface for both Consumers and Producers."""

    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        """Create Queue."""
        self.topic = topic
        self._type = _type
        self.content = LifoQueue()
        self._host = "localhost"
        self._port = 5000
        self._header = 2
        self.q_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.q_socket.connect((self._host, self._port))
        self.q_socket.setblocking(True)



    def push(self, value):
        """Sends data to broker. """
        pass

    def pull(self) -> (str, Any):
        """Waits for (topic, data) from broker.

        Should BLOCK the consumer!"""
        try:    
            msg_header = self.q_socket.recv(self._header)
            msg_len = int().from_bytes(msg_header, "big")
            if msg_len is not None:
                received_msg = self.q_socket.recv(msg_len)
                

            self.content.put(received_msg)
            return (self.topic, received_msg)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

    def list_topics(self, callback: Callable):
        """Lists all topics available in the broker."""
        pass
        
    def cancel(self):
        """Cancel subscription."""
        pass

#aqui temos que fazer o init e os outros métodos só que temos que fazer a conversão de cada tipo de serializacao 

class JSONQueue(Queue):
    """Queue implementation with JSON based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic,_type)
        self.q_socket.send(int(0).to_bytes(self._header, "big")) #send the serialization type
        self.q_socket.send(int(_type.value).to_bytes(self._header, "big")) #send the client type
        if(_type == MiddlewareType.CONSUMER):
            c = PubSub.subscribe(topic)
            subscribe_msg = c.get_dict()
            subscribe_msg = json.dumps(subscribe_msg)
            msg_len = len(subscribe_msg)
            self.q_socket.send(msg_len.to_bytes(2,"big") + subscribe_msg.encode('utf-8'))
            
            
        elif(_type == MiddlewareType.PRODUCER):
            c = PubSub.publish(None, topic)
            publish_msg = c.get_dict()
            publish_msg = json.dumps(publish_msg)
            msg_len = len(publish_msg)
            self.q_socket.send(msg_len.to_bytes(2,"big") + publish_msg.encode('utf-8'))
            
            
    def pull(self):
        self.topic, received_msg = super().pull()
        decoded_msg = json.loads(received_msg.decode("utf-8"))
        self.content.get()
        return (self.topic, decoded_msg["content"])


    def push(self, value):
        message = PubSub.publish(value, self.topic)
        message_json = json.dumps(message.get_dict())
        msg_len = len(message_json)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + message_json.encode('utf-8'))
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

    def list_topics(self, callback: Callable):
        message = str(PubSub.listTopics())
        message_json = json.dumps(message)
        msg_len = len(message_json)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + message_json.encode('utf-8'))
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)


    def cancel(self):
        message = str(PubSub.unsubscribe(self.topic))
        message_json = json.dumps(message)
        msg_len = len(message_json)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + message_json.encode('utf-8'))
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

class XMLQueue(Queue):
    """Queue implementation with XML based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic,_type)
        try:
            self.q_socket.send(int(0).to_bytes(self._header, "big")) #send the serialization type
            self.q_socket.send(int(_type.value).to_bytes(self._header, "big")) #send the client type
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)


        c = PubSub.subscribe(topic)
        subscribe_dict = c.get_dict()
        subscribe_msg = dict_to_xml("subscribe", subscribe_dict)
        msg_len = len(subscribe_msg)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + tostring(subscribe_msg))
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)


    def pull(self):
        self.topic, received_msg = super().pull()
        received_msg = etree_to_dict(received_msg.decode("utf-8"))
        self.content.get()
        return (self.topic, received_msg)

    def push(self, value):
        message = PubSub.publish(super().push(value), self.topic).get_dict()
        message_xml = dict_to_xml("message",message)
        msg_len = len(message_xml)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + tostring(message_xml))
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)


    def list_topics(self, callback: Callable):
        message = str(PubSub.listTopics())
        message_xml = dict_to_xml("list",message)
        msg_len = len(message_xml)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + tostring(message_xml))
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)


    def cancel(self):
        message = str(PubSub.unsubscribe(self.topic))
        message_xml = dict_to_xml("cancel" , message)
        msg_len = len(message_xml)

        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + tostring(message_xml))
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

class PickleQueue(Queue):
    """Queue implementation with Pickle based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic,_type)
        try:
            self.q_socket.send(int(2).to_bytes(self._header, "big")) #send the serialization type
            self.q_socket.send(int(_type.value).to_bytes(self._header, "big")) #send the client type
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

        if(_type == MiddlewareType.CONSUMER):
            c = PubSub.subscribe(topic)
            subscribe_msg = c.get_dict()
            subscribe_msg = pickle.dumps(subscribe_msg)
            msg_len = len(subscribe_msg)

            try:
                self.q_socket.send(msg_len.to_bytes(2,"big") + subscribe_msg)
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)
                sys.exit(1)
            
        elif(_type == MiddlewareType.PRODUCER):
            c = PubSub.publish(None, topic)
            publish_msg = c.get_dict()
            publish_msg = pickle.dumps(publish_msg)
            msg_len = len(publish_msg)
            try:
                self.q_socket.send(msg_len.to_bytes(2,"big") + publish_msg)
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)
                sys.exit(1)

    def pull(self):
        self.topic, received_msg = super().pull()
        received_msg = pickle.loads(received_msg.decode("utf-8"))
        self.content.get()
        return (self.topic, received_msg)

    def push(self, value):
        message = PubSub.publish(value, self.topic).get_dict()
        message_pickle = pickle.dumps(message)
        msg_len = len(message_pickle)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + message_pickle)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

    def list_topics(self, callback: Callable):
        message = str(PubSub.listTopics())
        message_pickle = pickle.dumps(message)
        msg_len = len(message_pickle)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + message_pickle)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)
            

    def cancel(self):
        message = str(PubSub.unsubscribe(self.topic))
        message_pickle = pickle.dumps(message)
        msg_len = len(message_pickle)
        try:
            self.q_socket.send(msg_len.to_bytes(2,"big") + message_pickle)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit(1)
            