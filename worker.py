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
		lastheardfrom = 0
		for entry in json_data:
			try:
				if entry["type"] == "manager" and entry["project"] == project_name and entry["lastheardfrom"] > lastheardfrom:
					self.host = entry["address"]
					self.port = int(entry["port"])
					lastheardfrom = int(entry["lastheardfrom"])
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

		# Listen to messages from manager about range of passwords to bruteforce
		self.listen_for_batch()


	def listen_for_batch(self):

		while True:
			#print('Waiting for batch...\n')
			# Read length of message from manager
			message_len = self.manager_sock.recv(8)
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
			crack = ""
			start = 0
			end = 0
			try:
				message_json = json.loads(message)
				crack = message_json["crack"]
				start = message_json["start"]
				end = message_json["end"]
			except:
				print("Invalid batch message received from manager or server disconnected")
				self.manager_sock.close()
				sys.exit(1)

			# Crack the current batch with the given range on the hashes that are not cracked yet
			self.crack_batch(crack, start, end)


	def crack_batch(self, crack, start, end):
		# 1.) Compute all potential passwords for given batch
		# 2.) Iterate over all hashes that are trying to be cracked
		# 3.) Compare hash with candidate if the hash hasn't been cracked already
		# 4.) If equals, password has been cracked

		#print("Computing batch: ")
		#print(crack)
		#print(f"Start: {start}, End: {end}\n")

		try:
			cracked_hashes = {}
			for candidate in self.get_candidates(start, end):
				cand_hash = hashlib.md5(candidate.encode()).hexdigest()
				for password_hash in crack:
					if cand_hash == password_hash:
						cracked_hashes[cand_hash] = candidate
		except:
			self.respond_failure()

		#print("Done with batch.")
		if cracked_hashes:
			print(f"Start: {start}, End: {end}")
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
				if l == length2:
					end = end_data[1]
				else:
					end = (SYMBOLS ** l) - 1
			elif l == length2:
				start = 0
				end = end_data[1]
			else:
				start = 0
				end = (SYMBOLS ** l) - 1
	
			start_list = [0] * l
			i = l - 1
			while start > 0:
				start_list[i] = start % SYMBOLS
				start //= SYMBOLS
				i -= 1

			end_list = [0] * l
			i = l - 1
			while end > 0:
				end_list[i] = end % SYMBOLS
				end //= SYMBOLS
				i -= 1

			while start_list != end_list:
				i = l - 1
				while i >= 0:
					candidate = "".join([cm.int_to_char[c] for c in start_list])
					yield candidate
					start_list[i] += 1
					if start_list[i] == SYMBOLS:
						start_list[i] = 0
						i -= 1
					else:
						break
			candidate = "".join([cm.int_to_char[c] for c in start_list])
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
