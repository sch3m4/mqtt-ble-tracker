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
				rssi += dev.rssi
				rssi /= 2
			else:
				devlist[dev.addr] = dev.rssi
				rssi = dev.rssi

			name = None
			for (adtype, desc, value) in dev.getScanData():
				if adtype == 9:
					name = value

			print("{} ({}), RSSI={} dB, RSSIAvg={:.4f}".format(dev.addr, name, dev.rssi , rssi))


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
