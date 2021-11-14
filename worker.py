#!/usr/bin/env python3

import socket
import json
import requests
import sys
import hashlib
import charmap
import os

SYMBOLS = 67

class Worker:

	def __init__(self):
		self.run_worker()


	def usage(self, status):
		progname = os.path.basename(sys.argv[0])
		print(f'Usage: ./{progname} manager-project-name')
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
		try:
			self.manager_sock.connect((self.host, self.port))
		except:
			print("Server not awake. Try again later.")
			sys.exit(1)

		# Send manager password for authenticity and say its ready for batches
		message = json.dumps({"status": "ready", "password": "dogecoin123"})
		message = len(message).to_bytes(8, "little") + message.encode("ascii")
		self.manager_sock.sendall(message)

		# Listen to messages from manager about range of passwords to bruteforce
		self.listen_for_batch()


	def listen_for_batch(self):

		while True:
			print('Waiting for batch...\n')
			# Read length of message from manager
			message_len = self.manager_sock.recv(8)
			if not message_len:
				self.manager_sock.close()
				print("Server disconnected.")
				sys.exit(1)
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
			cracked = ""
			start = 0
			end = 0
			try:
				message_json = json.loads(message)
				cracked = message_json["cracked"]
				start = message_json["start"]
				end = message_json["end"]
			except:
				print("Invalid batch message received from manager.")
				self.manager_sock.close()
				sys.exit(1)

			# Crack the current batch with the given range on the hashes that are not cracked yet
			self.crack_batch(cracked, start, end)


	def crack_batch(self, cracked, start, end):
		# 1.) Compute all potential passwords for given batch
		# 2.) Iterate over all hashes that are trying to be cracked
		# 3.) Compare hash with candidate if the hash hasn't been cracked already
		# 4.) If equals, password has been cracked

		print("Computing batch: ")
		print(cracked)
		print(f"Start: {start}, End: {end}\n")
		cracked = [h for h in cracked.keys() if not cracked[h]]

		try:
			cracked_hashes = {}
			for candidate in self.get_candidates(start, end):
				cand_hash = hashlib.md5(candidate.encode()).hexdigest()
				for password_hash in cracked:
					if cand_hash == password_hash:
						cracked_hashes[cand_hash] = candidate
		except:
			self.respond_failure()

		print("Done with batch.")
		print(f"Cracked: {cracked_hashes}\n\n")
		self.respond_success(cracked_hashes)


	def get_candidates(self, start_data, end_data):
		# Get all potential password candidates for the given batch
		cm = charmap.charmap()
		length1 = start_data[0]
		length2 = end_data[0]
		for l in range(length1, length2 + 1):
			start = 0
			end = 0
			if l == length1:
				start = start_data[1]
				end = SYMBOLS ** l
			elif l == length2:
				start = 0
				end = end_data[1]
			else:
				start = 0
				end = SYMBOLS ** l
			
			for code in range(start, end):
				candidate = ['0'] * l
				i = l
				while code > 0:
					candidate[i - 1] = cm.int_to_char[code % SYMBOLS]
					code //= SYMBOLS
					i -= 1
				c = "".join(candidate)
				candidate = "".join(candidate)
				yield candidate


	def respond_success(self, cracked_hashes):
		# Respond success to manager - success means there were no errors, not necessarily that a password was cracked
		message = json.dumps({'status': 'success', 'cracked': cracked_hashes})
		message = len(message).to_bytes(8, "little") + message.encode("ascii")
		self.manager_sock.sendall(message)


	def respond_failure(self):
		# Respond failure to manager - something failed while cracking passwords
		message = json.dumps({'status': 'failed'})
		message = len(message).to_bytes(8, "little") + message.encode("ascii")
		self.manager_sock.sendall(message)


	def run_worker(self):
		# Parse command line arguments
		args = sys.argv[1:]

		if len(args) == 0:
			self.usage(1)
		if args[0] == "-h":
			self.usage(0)

		# Query name server to get host and port
		project_name = args[0]
		self.query_ns(project_name)

		self.connect_to_manager()

if __name__ == '__main__':
	worker = Worker()