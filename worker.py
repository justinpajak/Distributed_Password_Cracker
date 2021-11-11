#!/usr/bin/env python3


import socket, json, requests, sys

class Worker:

	def __init__(self):
		self.run_worker()

	def usage(self, status):
		sys.exit(status)

	def query_ns(self, project_name):
		# Make HTTP request to catalog name server and fetch query.json file
		response = requests.get("http://catalog.cse.nd.edu:9097/query.json")
		json_data = json.loads(response.text)
	
		# Find entry corresponding to manager project name
		self.host = None
		self.port = None
		for entry in json_data:
			try:
				if entry["type"] == "manager" and entry["project"] == project_name:
					self.host = entry["address"]
					self.port = int(entry["port"])
			except:
				pass

		# Ensure query was successful
		if self.host == None or self.port == None:
			sys.stderr.write("Name server query invalid.")
			sys.exit(1)
	
	def connect_to_manager(self):
		# Create socket to connect to manager
		self.manager_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.manager_sock.connect((self.host, self.port))

		# Send manager password for authenticity and say its ready for batches
		message = json.dumps({"status": "ready", "password": "dogecoin123"})
		message = len(message).to_bytes(8, "little") + message.encode("ascii")
		self.manager_sock.sendall(message)
		
		# Listen to messages from manager about range of passwords to bruteforce
		self.listen_for_batch()

	def listen_for_batch(self):
		# Read length of message from manager
		message_len = self.manager_sock.recv(8)
		if not message_len:
			self.manager_sock.close()
			return
		message_len = int.from_bytes(message_len, "little")

		# Read message from manager
		message = ""
		total_read = 0
		while True:
			data = self.manager_sock.recv(512).decode("ascii")
			total_read += len(data)
			message += data
			if total_read == message_len:
				break
		
		# Determine if batch is valid and get cracked dict, start, and end range values
		message_json = {}
		try:
			message_json = json.loads(message)
			self.cracked = message_json["cracked"]
			self.start = message_json["start"]
			self.end = message_json["end"]
		except:
			self.manager_sock.close()
			return	

	def run_worker(self):
		# Parse command line arguments
		args = sys.argv[1:]

		if len(args) == 0:
			usage(1)
		if args[0] == "-h":
			usage(0)

		# Query name server to get host and port
		project_name = args[0]
		self.query_ns(project_name)
		print(self.host)
		print(self.port)
		self.connect_to_manager()

if __name__ == '__main__':
	worker = Worker()
