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


class BLEScanner():
	def __init__(self):
		self.scanner = Scanner()
	
	def scan(self,period=10):
		return self.scanner.scan(period)


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
		self.devlist = {'rssi':{},'tstamps':{}}
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


	def __send_message(self,msg):
		if self.verbose:
			print(msg)

		payload = json.dumps(msg)
		self.mqtt.publish(self.config['mqtt']['topic'],payload,self.config['mqtt']['qos'])


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

				self.__send_message(msg)


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

		# update the RSSI list for that device
		rssi_list = self.devlist['rssi'].get(dev.addr,list())
		if len(rssi_list) == self.config['ma_window']:
			rssi_list.pop(0)
		rssi_list.append(dev.rssi)
		self.devlist['rssi'][dev.addr] = rssi_list

		# get the MA
		ma_rssi = float("{:.2f}".format(self.__get_mavgs(rssi_list)[-1]))

		# calculate the distance with the  MA
		distance = math.pow ( 10 , ( devcfg['measured_power'] - ma_rssi ) / ( 10 * devcfg['n'] ) )

		# build and send the message
		msg = self.__build_message(
			devcfg['mac'],
			devcfg['name'],
			float("{:.2f}".format(distance)),
			self.__get_location(distance,devcfg),
			ma_rssi
		)
		self.__send_message(msg)
	

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
			self.devlist['rssi'][mac] = []
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
