import socket
import json
import os
import threading
import time
import select

import charmap

SYMBOLS = 91
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
        self.workers = {}
        self.hashes = []
        self.batch_size = batch_size
        self.intervals = {
            "available": [[0, SYMBOLS**max_length - 1]],
            "working": []
        } 

    def load_hashes(self, filename):
        with open(filename, 'r') as fr:
            self.hashes = [line.strip() for line in fr.readlines()]

    def batch(self):
        if not self.intervals["available"]:
            return None

        start = self.intervals["available"][0][0]
        end = min(self.intervals["available"][0][1], start+self.batch_size)
        self.intervals["available"][0][0] = end+1

        if self.intervals["available"][0][1] <= self.intervals["available"][0][0]:
            self.intervals["available"].pop(0)

        self.intervals["working"].append((start, end))

        return start, end


def update_ns(name, port):
    while True:
        server_info = {
            "type": "manager",
            "owner": os.environ['USER'],
            "port": port,
            "name": name
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.sendto(json.dumps(server_info).encode('utf-8'), (NS_HOST, NS_PORT))
        time.sleep(60)

if __name__ == "__main__":
    m = Manager(3, 9999)
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
            else:
                try:
                    pass
                    #m.accept_worker(s)
                except ConnectionResetError:
                    pass
                    #m.cleanup(s)
                

