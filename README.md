# Distributed Password Cracker
<h3> Developers: Justin Pajak and Erik Meier </h3>

- The purpose of this system is to serve as a distributed md5 hash cracking service that can discover plaintexts associated with a series of hashes.
- It accomplishes this through a Manager-Worker architecture where the manager evenly distributes potential ranges of plaintexts to connected worker nodes that individually brute-force their assigned range.  
- Each worker computes md5 on the range of plaintexts and compares the results with the list of hashes desired to be cracked.

<h3> Applications: </h3>
While the purposes of this system appear to be solely malicious, this tool can be used for research in the field of Cybersecurity.  Through our system, we have shown the feasibility of a bad-actor to create a distributed system that can brute force passwords assuming he/she knows the hashes of the passwords and the cryptographic hash that was applied to it.  One can assess the strength of their password by running our system using a chosen number of workers and analyzing how long it took the system to crack the password. In the future, the system will adapted so it could crack a variety of more commonly used hashes other than md5 such as SHA-256 and SHA-3.

<h3> Build and Run: </h3>
1.) On one machine, run a instance of the Manager process: ./manager.py
<br/>
2.) On one or several other machines, spawn one or several instances of the Worker process: ./worker.py dps-manager
<br/>
3.) The user on the manager side can now interact with the Manager CLI.
<br/>
<h3> Example: </h3>
Given a file, hash.txt, containing one md5 hash per line of passwords up to length 4 characters.
<br/>
In the Manager CLI, enter the following commands:
<br/>
<h4>> length 4</h4>
<h4>> add hash.txt </h4>
<br/>
The Manager will now begin distributing ranges of passwords to the Workers to brute-force and compare against the list of hashes from hash.txt
<br/>
<br/>
Type "prog" in the Manager CLI to see the progess bar for the current workload
<br/>
Type "system" in the Manager CLI to see a list of connected worker nodes and the last time the Manager heard from them.
<br/>
<h3> Warning </h3>
Upon killing the Manager process, a new Manager can not be created until the dps-manager entry in the catalog.cse.nd.edu:9097 name server has been removed.  This entry is removed around 15 minutes after the Manager process ends. This is because upon creating a new Manager instance, there will be two name server entries in catalog.cse.nd.edu:9097/query.json and the Worker nodes will not know which one is correct.  
