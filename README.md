## BLE Tracker
This project was made to reuse RPI/OSMC devices as BLE tracker, but it can work on any Linux machine with a Bluetooth device.

## Prerequisites
- On Debian based machines:
```
apt-get install python3-pip python3-setuptools libglib2.0-dev build-essential git
```

- Clone the repository
```
git clone https://github.com/sch3m4/bletracker.git
cd bletracker
```

- Install Python dependencies:
```
pip3 install requirements.txt
```

## Discovering and setting up your devices
### Distance calculation
There are lot of different ways to estimate the distance to the BLE device, here we're using the formula:

 ```
 distance = 10 ^ ( (MR — RSSI) / (10 * N) )
 ```

For the software to be able to calculate the distance to your device, you need to provide three parameters per each BLE device:
1. **RSSI**: Received signal strength indicator from the device to track
2. **MR**: RSSI at 1 meter
2. **N**: Constant (set between 2 and 4, depending on environment conditions)

### Discovering and adjustment
To discover and calculate the "**N**" constant, run the script with the following arguments:
```
python3 src/tracker.py --scan
```
   

## How to use
1. Clone the repository
2. Install "requirements.txt
2. Move the project folder to your prefered location
3. Edit the "src/bletracker.service" and set the right paths to "WorkingDirectory" and "ExecStart"
4. Adjust your settings in "config.yaml"
5. Install the service
    cp src/bletracker.service /etc/systemd/system/
    systemctl enable bletracker
6. You're ready to go
    systemctl start bletracker
