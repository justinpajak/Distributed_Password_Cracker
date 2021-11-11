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
		pass

	# Main worker code
	def run_worker(self):
		args = sys.argv[1:]

		if len(args) == 0:
			usage(1)
		if args[0] == "-h":
			usage(0)

		project_name = args[0]
		self.query_ns(project_name)
		print(self.host, self.port)

if __name__ == '__main__':
	worker = Worker()
