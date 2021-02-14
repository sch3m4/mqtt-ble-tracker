#!/usr/bin/env python3
#

import signal
import argparse
import threading

from bletracker import BLEracker,BLEScanner
from lib.kalman import SingleStateKalmanFilter

CONFIG_PATH = "config.yaml"

exitevt = threading.Event()


def handle_exit(signal,frame):
	exitevt.set()


def monitor(verbose):
	btracker = BLEracker(verbose)
	btracker.get_config(CONFIG_PATH)
	btracker.run_consumer()

	while not exitevt.is_set():
		btracker.scan()

	btracker.stop()


def scan(maclist):
	scanner = BLEScanner()
	devlist = {}

	while not exitevt.is_set():
		for dev in scanner.scan():
			if len(maclist) > 0 and dev.addr not in maclist:
				continue

			if dev.addr not in devlist.keys():

				A = 1 # no process innovation
				C = 1 # measurement
				B = 0 # no control input
				Q = 0.005 # process covariance
				R = 1 # measurement covariance
				x = dev.rssi # initial estimate
				P = 1 # initial covariance
				devlist[dev.addr] = SingleStateKalmanFilter(A,B,C,x,P,Q,R)

			devlist[dev.addr].step(0,abs(dev.rssi))

			name = None
			for (adtype, desc, value) in dev.getScanData():
				if adtype == 9:
					name = value

			# calculate distance with the smoothed RSSI
			frssi = -1 * devlist[dev.addr].current_state()
			n = scanner.get_n(frssi,dev.rssi)
			dist = scanner.get_distance(dev.rssi,frssi,n)
			print("{} ({}), RSSI={} dB, MR={:.4f}, N={:.8f}, Distance={:.2f}".format(dev.addr, name, dev.rssi , frssi, n,dist))


def main():
	signal.signal(signal.SIGINT, handle_exit )
	signal.signal(signal.SIGTERM, handle_exit )
	exitevt.clear()


	parser = argparse.ArgumentParser()
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("--scan",help="Scan for devices showing the avearage RSSI (",action="store_true")
	group.add_argument("--monitor",help="Monitor for registered devices",action="store_true")
	parser.add_argument("--device",nargs='+',help="Filter by device mac when scanning",default=[])
	parser.add_argument("--verbose",help="Run in verbose mode",action="store_true",default=False)
	args = parser.parse_args()


	if args.monitor:
		monitor(args.verbose)
	elif args.scan:
		scan(args.device)


if __name__ == "__main__":
	main()
