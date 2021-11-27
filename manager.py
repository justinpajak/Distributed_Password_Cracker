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
        self.cracked = []
        self.batch_size = batch_size
        self.available = [[length, 0, SYMBOLS**length - 1] for length in range(1,
            max_length+1)]
        self.working = []

    def load_hashes(self, filename):
        with open(filename, 'r') as fr:
            self.hashes = [line.strip() for line in fr.readlines()]

    def batch(self):
        if not self.available:
            return None, None
        
        to_batch = self.batch_size
        start = [self.available[0][0], self.available[0][1]]
        end = [0, 0]
        while to_batch > 0:
            if to_batch >= self.available[0][2] - self.available[0][1]:
                if len(self.available) == 1:
                    end[0], end[1] = self.available[0][0], self.available[0][2]
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
        order = {"crack": [h for h in self.hashes], "start": [start[0], start[1]], "end": [end[0], end[1]]}
        
        message = json.dumps(order)
        message = len(message).to_bytes(8, "little") + message.encode("ascii")
        conn.sendall(message)
        print(f"Sent interval to {conn.fileno}: {start} {end}")

    def update_worker(self, conn):
        # Receive message from worker
        message_len = conn.recv(8)
        message_len = int.from_bytes(message_len, "little")

        message = ""
        while len(message) < message_len:
            message += conn.recv(512).decode("ascii")

        message_json = json.loads(message)
        if message_json['status'] == 'failure':
            raise ConnectionResetError
        cracked = message_json['cracked']
        for c in cracked:
            self.hashes.remove(c)
            self.cracked.append((cracked[c], c))

        # Update manager-side info
        self.workers[conn.fileno()]["lastheardfrom"] = time.time()
        start, end = self.batch()
        self.workers[conn.fileno()]["interval"] = (start, end)
        
        # Update worker with new batch
        order = {"crack": [h for h in self.hashes], "start": [start[0], start[1]], "end": [end[0], end[1]]}

        conn.sendall(json.dumps(order).encode('utf-8'))
        print(f"Sent interval to {conn.fileno()}: {start} {end}")

    def cleanup(self, conn):
        w = self.workers.pop(conn.fileno())
        if w["interval"] not in self.working:
            return
        self.working.remove(w["interval"])
        for length in range(w["interval"][0][0], w["interval"][1][0]+1):
            if length == w["interval"][0][0]:
                self.available.insert(0, [length, w["interval"][0][1], SYMBOLS**length - 1])
            elif length == w["interval"][1][0]:
                self.available.insert(0, [length, 0, w["interval"][1][1]])
            else:
                self.available.insert(0, [length, 0, SYMBOLS**length - 1])

        print("Available Intervals: ", self.available)
         

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
            "project": name
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
    else:
        print("Invalid Command")
    print("> ", end="", flush=True)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
    m = Manager(3, 9999)
    m.load_hashes(sys.argv[1])
    hostname = socket.gethostbyname(socket.gethostname())
    projname = "dps-manager"

    # Open up server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((hostname, 0))
    port = server.getsockname()[1]
    socks = [server, sys.stdin]
    server.listen()
    
    # Start thread to constantly update name server
    ns_thread = threading.Thread(target=update_ns, args=(projname, port))
    ns_thread.start()
    
    # Set up interactive shell
    os.system('clear')
    print(f"Distributed Password Cracker - Manager (Port {port})")
    print("-- type help for command list")
    print("\n> ", end="", flush=True)
    
    # Main loop
    while True:
        r, w, x = select.select(socks, [], [])
        for s in r:
            if s == server:
                conn, addr = s.accept()
                print("New worker with id {conn.fileno()}")
                socks.append(conn)
                m.accept_worker(conn)
            elif s == sys.stdin:
                try:
                    handle_input(m, sys.stdin.readline().strip())
                except:
                    print("Invalid Command")
                    print("> ", end="", flush=True)
            else:
                try:
                    m.update_worker(s)
                except:
                    m.cleanup(s)
                    socks.remove(s)
                

