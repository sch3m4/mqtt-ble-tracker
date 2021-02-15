#!/usr/bin/env python3
#

import json
import math
import yaml
import time
import threading
import numpy as np

from multiprocessing import Queue
from paho.mqtt import client as mqtt_client
from bluepy.btle import Scanner, DefaultDelegate

from lib.kalman import SingleStateKalmanFilter


class BLEScanner():
	def __init__(self):
		self.scanner = Scanner()
	
	def scan(self,period=10):
		return self.scanner.scan(period)

	def get_n(self,mr,rssi,distance=1.0):
		return 2 + abs ( ( (mr - rssi) * math.log(math.e,10) ) / 10 )

	def get_distance(self,rssi,mr,n):
		if n == 0:
			return -1
		return math.pow ( 10 , (mr - rssi) / (10 * n ) )


class BLEracker():

	# Handle the devices discovery by using this class 
	# to not to wait for the scan to finish
	class Callback(DefaultDelegate):
		def __init__(self,queue,watchlist):
			DefaultDelegate.__init__(self)
			self.__queue = queue
			self.__watchlist = watchlist

		def handleDiscovery(self, dev, isNewDev, isNewData):
			if dev.addr in self.__watchlist:
				self.__queue.put(dev)


	def __init__(self,verbose = False):
		self.scanner = None
		self.exitevt = threading.Event()
		self.queue = Queue()
		self.consumer = None
		self.watchlist = None
		self.devlist = {'tstamps':{},'kalman':{}}
		self.locations = {'ranges':[],'labels':[]}
		self.config = None
		self.mqtt = None
		self.verbose = verbose


	def __get_mavgs(self,values):
		window = len(values)
		weights = np.repeat(1.0, window)/window
		sma = np.convolve(values, weights, 'valid')
		return sma


	def __get_location(self,distance,devcfg):
		for idx,entry in enumerate(self.locations['ranges']):
			a,b = entry
			# if in range
			if a < distance and distance < b:
				return self.locations['labels'][idx]
		# not in range
		return devcfg['status_off']


	def __build_message(self,devid,name,distance,location=None,rssi=-1):
		msg = {
			'id' : devid,
			'name' : name,
			'distance' : distance,
		}

		include_loc = self.config['messages'].get('include_location',False)
		include_rssi = self.config['messages'].get('include_rssi',False)

		if include_loc and location:
			msg['location'] = location
		if include_rssi:
			msg['rssi'] = rssi

		return msg


	def __send_message(self,msg,location):
		if self.verbose:
			print(msg)

		# running in single tracker mode?
		single_tracker = self.config.get('single_tracker',False)
		if single_tracker:
			topic = "{}/{}".format(self.config['mqtt']['topic'],location)
		else:
			topic = self.config['mqtt']['topic']

		payload = json.dumps(msg)
		self.mqtt.publish(topic,payload,self.config['mqtt']['qos'])


	def __check_timeouts(self):
		now = int(time.time())
		items = self.devlist['tstamps'].keys()
		for dev in items:
			tstamp = self.devlist['tstamps'].get(dev,0)
			devcfg = next((x for x in self.config['devices'] if x['mac'] == dev),dict())
			timeout = devcfg.get('timeout',0)

			# device timed out
			if timeout > 0 and now - tstamp > timeout:
				self.devlist['tstamps'][dev] = now

				msg = self.__build_message(
					dev,
					devcfg['name'],
					-1,
					devcfg['status_off'],
					-1
				)

				self.__send_message(msg,devcfg['status_off'])


	def __process_queue(self):
		try:
			dev = self.queue.get(False)
		except:
			dev = None
		
		self.__check_timeouts()

		if dev is None:
			return

		# untracked device
		devcfg = next((x for x in self.config['devices'] if x['mac'] == dev.addr),None)
		if devcfg is None:
			return

		# update the timestamp
		self.devlist['tstamps'][dev.addr] = int(time.time())


		# verify RSSI threshold
		min_rssi = devcfg.get('min_rssi',-200)
		if dev.rssi < min_rssi:
			return
		

		# get the kalman filter for the device
		kalmanf = self.devlist['kalman'].get(dev.addr,None)
		if not kalmanf:
			A = 1 # no process innovation
			C = 1 # measurement
			B = 0 # no control input
			Q = 0.005 # process covariance
			R = 1 # measurement covariance
			x = dev.rssi # initial estimate
			P = 1 # initial covariance
			self.devlist['kalman'][dev.addr] = SingleStateKalmanFilter(A,B,C,x,P,Q,R)		

		# get the MA
		kalmanf = self.devlist['kalman'][dev.addr]
		kalmanf.step(0,dev.rssi)
		rssi = kalmanf.current_state()

		# calculate the distance with the  MA
		distance = math.pow ( 10 , ( devcfg['measured_power'] - rssi ) / ( 10 * devcfg['n'] ) )

		# get the location
		location = self.__get_location(distance,devcfg)

		# build and send the message
		msg = self.__build_message(
			devcfg['mac'],
			devcfg['name'],
			float("{:.2f}".format(distance)),
			location,
			rssi
		)
		self.__send_message(msg,location)
	

	def __consumer(self):
		while not self.exitevt.is_set():
			self.__process_queue()

		while not self.queue.empty():
			self.__process_queue()


	def get_config(self,path):
		with open(path,"rt") as fd:
			self.config = yaml.load(fd,Loader=yaml.FullLoader)

		# map the devices MAC to a list
		self.watchlist = [x['mac'] for x in self.config['devices']]

		# map the devices to timestamps and rssi
		for mac in self.watchlist:
			self.devlist['kalman'][mac] = None
			self.devlist['tstamps'][mac] = 0

		# map the locations and labels to local vars
		locations = self.config.get('locations',dict())
		for loc in locations.keys():
			a = locations[loc]['min_dist']
			b = locations[loc]['max_dist']
			self.locations['ranges'].append([a,b])
			self.locations['labels'].append(loc)


	def run_consumer(self):
		# scanner object
		self.scanner = Scanner().withDelegate(
			self.Callback(self.queue,self.watchlist,)
			)

		# mqtt connection
		self.mqtt = mqtt_client.Client(self.config['mqtt']['name'])

		# mqtt authentication
		user = self.config['mqtt'].get('username',None)
		pwd = self.config['mqtt'].get('password',None)
		if user and pwd:
			self.mqtt.username_pw_set(user,pwd)
		
		# mqtt connection
		self.mqtt.connect(self.config['mqtt']['host'],self.config['mqtt']['port'],self.config['mqtt']['keepalive'])
		self.mqtt.connect
		self.mqtt.loop_start()

		# consumer thread
		self.consumer = threading.Thread(target=self.__consumer)
		self.consumer.start()


	def scan(self):
		self.scanner.scan(self.config['scan_period'])

	
	def stop(self):
		self.exitevt.set()
		self.consumer.join()
		self.mqtt.loop_stop()
