import requests
import time
import threading
import math
import json
import argparse

from netaddr import IPNetwork

args = {}

##############################

something={}
nothing={}
mutex = threading.Lock()

def worker(index, list, accounter):
	global something, nothing, mutex, args
	print("Starting T"+str(index))
	start = time.time()
	tm = args['timeout']
	accounter['processed'][index] = 0
	accounter['goal'][index] = len(list)

	for ip in list:
		try:
			response = requests.get('http://'+str(ip), timeout=tm)
			#print ("T"+str(index)+" "+str(ip)+ ":" + str(response.status_code))
			try:
				something[str(response.status_code)].append(str(ip))
			except KeyError:
				mutex.acquire()
				if str(response.status_code) not in something:
					something[str(response.status_code)] = []
				mutex.release()
		except Exception as e:
			#print ("T"+str(index)+" "+str(ip) + " is down, reason: " + str(type(e)))
			try:
				nothing[str(type(e))].append(str(ip))
			except KeyError:
				mutex.acquire()
				if str(type(e)) not in nothing:
					nothing[str(type(e))] = []
				mutex.release()	

		finally:

			accounter['processed'][index] += 1
	accounter['elapsed'][index] = (time.time() - start)


def main():
	global args

	threads = args['workers']
	lst= list(IPNetwork(args['target'].replace("'", "")))
	llist = len(lst)
	chunk = math.floor(llist/threads)
	trail = llist%threads
	
	th = []
	accounter = {}
	accounter['elapsed'] = [None]*threads
	accounter['goal'] = [0]*threads
	accounter['processed'] = [0]*threads

	for i in range(threads-1):
		th.append(threading.Thread(target=worker, args=[i, lst[i*chunk:(i+1)*chunk], accounter]))

	th.append(threading.Thread(target=worker, args=[threads-1, lst[((threads-1)*chunk):((threads)*chunk+trail)], accounter]))

	start = time.time()

	for i in th:
		i.start()

	while None in accounter['elapsed']:
		print("TOTAL:"+str(sum(accounter['processed']))+"/"+str(llist), end=" ")
		for i in range(threads):
			print("T"+str(i)+":"+str(accounter['processed'][i])+"/"+str(accounter['goal'][i]), end=" ")
		print("", end="\r")
	
	print("Scan took: " + str(time.time() - start))

	with open(args['out'].replace("'", ""), 'w') as fp:
		json.dump({'successes': something, 'errors': nothing}, fp, indent=4)


if __name__=="__main__":

	parser = argparse.ArgumentParser(description='Finds web servers...')
	parser.add_argument('-t', '--target', type=ascii, help='cidr notation of target network', required=True)
	parser.add_argument('-w', '--workers', type=int, help='number of threads', default=16, nargs='?')
	parser.add_argument('-T', '--timeout', type=float, help='timeout of each request', default=1, nargs='?')

	parser.add_argument('-o', '--out', type=ascii, help='destination file', required=True)
	
	args = vars(parser.parse_args())
	
	main()