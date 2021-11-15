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
        self.workers = {}
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
        self.workers[conn.fileno()] = {"conn": conn, "lastheardfrom": time.time()}
        start, end = self.batch()
        self.workers[conn.fileno()]["interval"] = (start, end)
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

def handle_input(m, command):
    command = command.split(' ')
    if command[0] == "help":
        print("Command List:")
        print("    help: show this menu")
        print("    add <hash>: add hash string <hash> to workload")
        print("    addfile <hashfile>: add hashes in file <hashfile> to workload")
        print("    system: display system information")
    elif command[0] == "add":
        print(command[1])
    elif command[0] == "addfile":
        print(command[1])
    elif command[0] == "system":
        print(m.workers)
    print("> ", end="", flush=True)

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
    socks = [server, sys.stdin]
    print(f'Manager listening on port {port}')
    server.listen()
    
    ns_thread = threading.Thread(target=update_ns, args=(projname, port))
    ns_thread.start()
    
    os.system('clear')
    print("Distributed Password Cracker - Manager")
    print("-- type help for command list")
    print("\n> ", end="", flush=True)
    while True:
        r, w, x = select.select(socks, [], [])
        for s in r:
            if s == server:
                conn, addr = s.accept()
                print("New worker with id {conn.fileno()}")
                socks.append(conn)
                m.accept_worker(conn)
            elif s == sys.stdin:
                handle_input(m, sys.stdin.readline().strip())
            else:
                pass
                    #m.cleanup(s)
                

