"""Message Broker"""
import json
import pickle
import selectors
import socket
from typing import Any, Dict, List, Tuple
import sys
import traceback
from xml.etree.ElementTree import Element, tostring
from .enums import *
from .PubSub import PubSub


class Broker:
    """Implementation of a PubSub Message Broker."""

    def __init__(self):
        """Initialize broker."""
        self.canceled = False
        self._host = "localhost"
        self._port = 5000
        self._header = 2
        ##
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((self._host, self._port))
        self.s.listen()
        ##
        self.socket_list = [self.s]
        self.existing_topics = []       # topic_name
        self.topic_lst = {}             # topic --> key=topic_name | value:last_value, subtopics:[], subscribers:[]
        self.client_lst = {}            # client --> key=socket | addr: address type: "producer/consumer", serialization: Serializer.JSON/XML/PICKLE args: {published topics/subscribed topics}
        ##
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.s, selectors.EVENT_READ)



    def accept_client(self, incoming_socket):
        inc_client_sock , client_address = incoming_socket.accept()
        serialization = inc_client_sock.recv(self._header)
        serialization = Serializer(int().from_bytes(serialization, "big"))
        client_type = inc_client_sock.recv(self._header)
        client_type = MiddlewareType(int().from_bytes(client_type, "big"))
        self.register_client(inc_client_sock, client_address, serialization, client_type)


        
    def register_client(self, inc_client_sock, client_address, client_serialization, client_type):
        self.client_lst[inc_client_sock] = {"addr":client_address, "type":client_type, "serialization": client_serialization}
        self.socket_list.append(inc_client_sock)
        self.sel.register(inc_client_sock, selectors.EVENT_READ | selectors.EVENT_WRITE)

    def receive_msg(self, client_sock):
        received = PubSub.recv_msg(client_sock, self.client_lst[client_sock]["serialization"])
        return received

    def publish_msg(self, topic):
        for client in self.topic_lst[topic]["subscribers"]:
            publish_msg = PubSub.publish(self.get_topic(topic), topic)
            PubSub.send_msg(client[0], publish_msg, client[1])



    def list_topics(self) -> List[str]:
        """Returns a list of strings containing all topics."""
        return self.existing_topics

    def get_topic(self, topic):
        """Returns the currently stored value in topic."""
        if topic in self.topic_lst:
            return self.topic_lst[topic]["value"]
        
        return None


    def put_topic(self, topic, value):
        """Store the value in topic."""
        if topic not in self.existing_topics:
            self.topic_lst[topic] ={"value":value, "subtopics":[], "subscribers":[]}
            self.existing_topics.append(topic)
        else:
            self.topic_lst[topic]["value"] = value

    def list_subscriptions(self, topic: str) -> List[socket.socket]:
        """Provide list of subscribers to a given topic."""
        if topic in self.topic_lst:
            return self.topic_lst[topic]["subscribers"]
        
        return None

        

    def subscribe(self, topic: str, address: socket.socket, _format: Serializer = None):
        """Subscribe to topic by client in address."""
        if topic not in self.existing_topics:
            self.topic_lst[topic] ={"value":None, "subtopics":[], "subscribers":[(address, _format)]}
            self.existing_topics.append(topic)
        
        else:
            self.topic_lst[topic]["subscribers"].append((address, _format))

    def unsubscribe(self, topic, address):
        """Unsubscribe to topic by client in address."""
        for subscriber in self.topic_lst[topic]["subscribers"]:
            if subscriber[0] == address:
                self.topic_lst[topic]["subscribers"].remove(subscriber)
                    

    def run(self):
        """Run until canceled."""
        has_message = False
        has_list = False
        while not self.canceled:
            try:
                for analysing_socket, mask in self.sel.select():
                    if (analysing_socket.fileobj == self.s) :
                        self.accept_client(analysing_socket.fileobj)
                        has_message = False
                    else:
                        if(mask & selectors.EVENT_READ):
                        
                            received_msg = self.receive_msg(analysing_socket.fileobj)
                            if(received_msg is None):
                                del self.client_lst[analysing_socket.fileobj]
                                self.sel.unregister(analysing_socket.fileobj)
                                self.socket_list.remove(analysing_socket.fileobj)
                                continue
                            received_msg = received_msg.get_dict()


                            if(received_msg["command"]=="publish"):
                                self.put_topic(received_msg["topic"], received_msg["content"])
                                if received_msg["content"] is not None:
                                    self.publish_msg(received_msg["topic"])
                                    
                                
                                
                            elif(received_msg["command"] == "subscribe"):                                
                                self.subscribe(received_msg['topic'], analysing_socket.fileobj, self.client_lst[analysing_socket.fileobj]['serialization'])
                        
                            elif(received_msg["command"] == "unsubscribe"):
                                topic = received_msg["topic"]
                                self.unsubscribe(topic , analysing_socket.fileobj)

                            elif(received_msg["command"] == "list"):
                                topics = self.list_topics()
                                serialization = received_msg["serialization"]
                                has_list = True

                        if mask & selectors.EVENT_WRITE:
                            if has_message:
                                for receiving_socket in self.socket_list:
                                    if (receiving_socket != self.s):
                                        pass
                            
                            elif has_list:
                                PubSub.send_msg(analysing_socket.fileobj , topics , serialization)
                                has_message = False


            except KeyboardInterrupt:
                            self.s.shutdown(socket.SHUT_RDWR)
                            print("\nClosing server.")
                            sys.exit()
            










'''
    try:
                for analysing_socket, mask in self.sel.select():
                    if (analysing_socket.fileobj == self.s) :
                        self.accept_client(analysing_socket.fileobj)
                        has_message = False
                    else:
                        if(mask & selectors.EVENT_READ):
                        
                            received_msg = self.receive_msg(analysing_socket.fileobj)
                            if(received_msg is None):
                                del self.client_lst[analysing_socket.fileobj]
                                self.sel.unregister(analysing_socket.fileobj)
                                self.socket_list.remove(analysing_socket.fileobj)
                                continue
                            received_msg = received_msg.get_dict()

                            if(received_msg["command"]=="subscribe"):
                                message = received_msg["content"]
                                topic = received_msg["topic"]
                                self.put_topic(topic, message)
                                
                                #print(f"Received message from {self.clients[analysing_socket.fileobj]['user']} at {ts}: < {message} > , channel < {channel} >")
                                #logging.debug(f"Received message from {self.clients[analysing_socket.fileobj]['user']} at {ts}: < {message} > , channel < {channel} >")
                                has_message=True
                                

                                
                            elif(received_msg["command"] == "subscribe"):
                                self.subscribe( received_msg["topic"] , analysing_socket.fileobj)
                                #print(f"Client {self.clients[analysing_socket.fileobj]['user']} joined < {received_msg.channel} > channel.")
                            
                            elif(received_msg["command"] == "unsubscribe"):
                                self.unsubscribe( received_msg["topic"] , analysing_socket.fileobj )
                            
                            elif(received_msg["command"] == "list"):
                                topics = self.list_topics()
                                serialization = received_msg["serialization"]
                                has_list = True

                        if mask & selectors.EVENT_WRITE:
                            if has_message:
                                    self.publish_msg(topic, message)
                                    has_message = False
                            elif has_list:
                                PubSub.send_msg(analysing_socket.fileobj , topics , serialization)

            except KeyboardInterrupt:
                            self.s.shutdown(socket.SHUT_RDWR)
                            print("\nClosing server.")
                            sys.exit()
'''


