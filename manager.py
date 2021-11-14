import socket
import sys
import json
import os
import threading
import time
import select

import charmap

SYMBOLS = 67
NS_HOST = 'catalog.cse.nd.edu'
NS_PORT = 9097

class Manager:
    """
    Manager Class
    max_length: maximum length of password to crack
    batch_size: number of password combinations to dispatch to each worker at a
    time
    
    Properties:
    workers: dictionary containing worker information
    hashes: list of hashes to match against
    intervals: dictionary of password combination intervals that still need to
    be tried
    """
    def __init__(self, max_length, batch_size):
        self.workers = []
        self.hashes = []
        self.batch_size = batch_size
        self.available = [[length, 0, SYMBOLS**length - 1] for length in range(1,
            max_length+1)]
        self.working = []

    def load_hashes(self, filename):
        with open(filename, 'r') as fr:
            self.hashes = [line.strip() for line in fr.readlines()]

    def batch(self):
        if not self.available:
            return None
        
        to_batch = self.batch_size
        start = [self.available[0][0], self.available[0][1]]
        end = [0, 0]
        while to_batch > 0:
            if to_batch >= self.available[0][2] - self.available[0][1]:
                if len(self.available) == 1:
                    end[0], end[1] = self.available[0], self.available[2]
                    self.available.pop(0)
                    break
                else:
                    to_batch -= self.available[0][2] - self.available[0][1]
                    self.available.pop(0)
            else:
                end[0] = self.available[0][0]
                end[1] = self.available[0][1] + to_batch
                self.available[0][1] = end[1] + 1
                to_batch = 0

        self.working.append((start, end))

        return start, end

    def accept_worker(self, conn):
        w = {"conn": conn, "lastheardfrom": time.time()}
        start, end = self.batch()
        w["interval"] = (start, end)
        order = {"cracked": {}, "start": [start[0], start[1]], "end": [end[0], end[1]]}
        for h in self.hashes:
            order["cracked"][h] = False
        
        conn.sendall(json.dumps(order).encode('utf-8'))
        print("Sent work order", json.dumps(order).encode('utf-8'))


def usage():
    print(f"Usage: {sys.argv[0]} <hashfile>")
    print("    hashfile: name of file containing password hashes")
    sys.exit(1)

def update_ns(name, port):
    while True:
        server_info = {
            "type": "manager",
            "owner": os.environ['USER'],
            "port": port,
            "name": name
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(json.dumps(server_info).encode('utf-8'), (NS_HOST, NS_PORT))
        time.sleep(60)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
    m = Manager(3, 9999)
    m.load_hashes(sys.argv[1])
    hostname = socket.gethostname()
    projname = "dps-manager"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((hostname, 0))
    port = server.getsockname()[1]
    socks = [server]
    print(f'Manager listening on port {port}')
    server.listen()
    
    ns_thread = threading.Thread(target=update_ns, args=(projname, port))
    ns_thread.start()
    
    while True:
        r, w, x = select.select(socks, [], [])
        for s in r:
            if s == server:
                print("Found New Client")
                conn, addr = s.accept()
                socks.append(conn)
                m.accept_worker(conn)
            else:
                try:
                    pass
                    m.accept_worker(s)
                except ConnectionResetError:
                    pass
                    #m.cleanup(s)
                
