#!/usr/bin/env python3
#

import signal
import argparse
import threading
from bletracker import BLEracker,BLEScanner

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

			if dev.addr in devlist.keys():
				devlist[dev.addr]['rssi'].append(dev.rssi)
			else:
				devlist[dev.addr] = {'rssi' : [dev.rssi] , 'n' : 0 }

			name = None
			for (adtype, desc, value) in dev.getScanData():
				if adtype == 9:
					name = value

			rssi_abs = [abs(x) for x in devlist[dev.addr]['rssi']]
			avg = -1 * ( sum(rssi_abs) / len(rssi_abs) )

			n = scanner.get_n(avg,dev.rssi)
			devlist[dev.addr]['n'] += n
			devlist[dev.addr]['n'] /= 2
			n = devlist[dev.addr]['n']

			dist = scanner.get_distance(dev.rssi,avg,n)

			print("{} ({}), RSSI={} dB, MR={:.4f}, N={:.8f}, Distance={:.2f}".format(dev.addr, name, dev.rssi , avg, n,dist))


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
