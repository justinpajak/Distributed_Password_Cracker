import socket
import sys
import json
import os
import threading
import time
import select
import argparse


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
    cracked: list of password, hash tuples
    available: list of password combination intervals that still need to
    be tried
    working: list of password combination intervals currently being worked on
    """
    def __init__(self, max_length, batch_size):
        self.workers = {}
        self.hashes = []
        self.cracked = []
        self.available = [[length, 0, SYMBOLS**length - 1] for length in range(1, max_length+1)]
        self.batch_size = batch_size
        self.max_length = max_length
        self.working = []
        self.complete = False

    def load_hashes(self, filenames):
        self.hashes = []
        for filename in filenames:
            try:
                with open(filename, 'r') as fr:
                    self.hashes.extend([line.strip() for line in fr.readlines()])
            except:
                self.hashes.append(filename)
        self.available = [[length, 0, SYMBOLS**length - 1] for length in
                    range(1, self.max_length+1)]

    def batch(self):
        if not self.available:
            return None, None
        
        to_batch = self.batch_size-1
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
        self.workers[conn.fileno()] = {"conn": conn}
        self.send_work(conn)

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
        for c in message_json['cracked']:
            self.hashes.remove(c)
            pwd = message_json['cracked'][c]
            self.cracked.append((message_json['cracked'][c], c))

        # If workload is complete
        if not self.hashes or not self.available:
            self.complete = True
            print()
            if self.cracked:
                print("Finished Cracking. Results:")
                for msg, cipher in self.cracked:
                    print("    ", msg, "-", cipher)
            
            # print total time to complete workload
            duration = time.time() - start_time
            duration = float("{:.2f}".format(duration))
            print(f"Time: {duration} s")

            print("> ", end="", flush=True)
            self.cracked.clear()
            self.available = [[length, 0, SYMBOLS**length - 1] for length in range(1, self.max_length+1)]
            return

        self.send_work(conn)
    
    def send_work(self, conn):
        # Assign a new batch
        self.workers[conn.fileno()]["lastheardfrom"] = time.time()
        start, end = self.batch()
        self.workers[conn.fileno()]["interval"] = (start, end)
        
        # Update worker with new batch
        order = {"crack": [h for h in self.hashes], "start": [start[0], start[1]], "end": [end[0], end[1]]}

        message = json.dumps(order)
        message = len(message).to_bytes(8, "little") + message.encode("ascii")
        conn.sendall(message)

    def cleanup(self, conn):
        if conn.fileno not in self.workers:
            return

        w = self.workers.pop(conn.fileno())
        if w["interval"] not in self.working:
            return
        
        self.working.remove(w["interval"])
        if w["interval"][0][0] == w["interval"][1][0]:
            self.available.insert(0, [w["interval"][0][0], w["interval"][0][1], w["interval"][1][1]])
        else:
            for length in range(w["interval"][0][0], w["interval"][1][0]+1):
                if length == w["interval"][0][0]:
                    self.available.insert(0, [length, w["interval"][0][1], SYMBOLS**length - 1])
                elif length == w["interval"][1][0]:
                    self.available.insert(0, [length, 0, w["interval"][1][1]])
                else:
                    self.available.insert(0, [length, 0, SYMBOLS**length - 1])

    def display_progress(self):
        bar_length = 60
        full = sum((SYMBOLS**length for length in range(1, m.max_length+1)))
        curr = full - sum((i[1] - i[0] for i in self.available))
        bars = int(round(bar_length*(1- curr/full)))
        percent = abs(round(100*(1 - curr/full), 2))
        bar = "#"*bars + "-"*(bar_length-bars)
        print(f"[{bar}] {percent}%")
        if self.cracked:
            print("Cracked:")
            for msg, cipher in self.cracked:
                print("    ", msg, "-", cipher)

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
        s.close()
        time.sleep(60)

def handle_input(m, command):
    command = command.split(' ')
    if command[0] == "help":
        print("Command List:")
        print("    help: show this menu")
        print("    add <hash ...>: add hashes to workload (raw text or filenames)")
        print("    prog: show progress bar for current workload")
        print("    system: display system information")
        print("    length <length>: change max password length")
        print("    batch <size>: change batch size")
        print("    exit: exit the program")
    elif command[0] == "add":
        if not m.hashes or not m.available:
            m.load_hashes(command[1:])
            global start_time
            start_time = time.time()
        else:
            print('Error: Wait for current workload to finish')
    elif command[0] == "system":
        print(m.workers)
    elif command[0] == "prog":
        m.display_progress()
    elif command[0] == "length":
        try:
            m.max_length = int(command[1])
            self.available = [[length, 0, SYMBOLS**length - 1] for length in range(1, max_length+1)]
            print(f'Set max length to {m.max_length}')
        except IndexError:
            print(f'Current max length is {m.max_length}')
    elif command[0] == "batch":
        try:
            m.batch_size = int(command[1])
            print(f'Set batch size to {m.batch_size}')
        except IndexError:
            print(f'Current batch size is {m.batch_size}')
    elif command[0] == "exit":
        sys.exit(0)
    else:
        raise Exception
    print("> ", end="", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Distributed Password Cracker')
    parser.add_argument('--length', type=int, default=4, help='maximum length of password')
    parser.add_argument('--batch', type=int, default=10000, help='size of batch')
    parser.add_argument('hashfiles', nargs='*', type=str, help='hashes to crack')
    args = parser.parse_args()

    m = Manager(args.length, args.batch)
    if args.hashfiles:
        m.load_hashes(args.hashfiles)
    hostname = socket.gethostbyname(socket.gethostname())
    projname = "dps-manager"

    # Open up server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((socket.gethostname(), 0))
    port = server.getsockname()[1]
    socks = [server, sys.stdin]
    server.listen()
    
    # Start thread to constantly update name server
    ns_thread = threading.Thread(target=update_ns, args=(projname, port), daemon=True)
    ns_thread.start()
    
    # Set up interactive shell
    os.system('clear')
    print(f"Distributed Password Cracker - Manager (Port {port})")
    print("-- type help for command list")
    print("\n> ", end="", flush=True)
    
    # Main loop
    m.complete = m.hashes == []
    prev = time.time()
    while True:
        r, w, x = select.select(socks, [], [])
        for s in r:
            if s == sys.stdin:
                try:
                    handle_input(m, sys.stdin.readline().strip())
                except Exception as ex:
                    print("Invalid Command")
                    print("> ", end="", flush=True)
            elif m.hashes and m.available:
                if s == server:
                    conn, addr = s.accept()
                    print(f"\nNew worker with id {conn.fileno()}")
                    print("> ", end="", flush=True)
                    socks.append(conn)
                    m.accept_worker(conn)
                else:
                    try:
                        m.update_worker(s)
                    except:
                        m.cleanup(s)
                        socks.remove(s)
        if m.complete:
            if not m.hashes:
                continue

            # Restart all workers
            for s in socks:
                if s == sys.stdin or s == server:
                    continue
                m.send_work(s)
            m.complete = False
        else:
            # Check for timeouts every 5 seconds
            curr = time.time()
            if curr - prev < 5:
                continue
            prev = curr
            for fn in list(m.workers):
                if curr - m.workers[fn]['lastheardfrom'] > 30:
                    m.cleanup(m.workers[fn]['conn'])

