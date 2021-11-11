#!/usr/bin/env python3

import socket, json, requests, sys

def query_ns(project_name):
	# Make HTTP request to catalog name server and fetch query.json file
	response = requests.get("http://catalog.cse.nd.edu:9097/query.json")
	json_data = json.loads(response.text)
	
	# Find entry corresponding to manager project name
	host = None
	port = None
	for entry in json_data:
		try:
			if entry["type"] == "manager" and entry["project"] == project_name:
				host = entry["address"]
				port = int(entry["port"])
		except:
			pass

	# Ensure query was successful
	if host == None or port == None:
		sys.stderr.write("Name server query invalid.")
		sys.exit(1)
	
	return host, port

def usage(status):
	sys.exit(status)

# Main worker code
def run_worker():
	args = sys.argv[1:]

	if len(args) == 0:
		usage(1)
	if args[0] == "-h":
		usage(0)

	project_name = args[0]
	host, port = query_ns(project_name)
	print(host, port)

if __name__ == '__main__':
	run_worker()
