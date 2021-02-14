## BLE Tracker
This project was made to reuse RPI/OSMC devices as BLE tracker, but can work on any Linux machine with a Bluetooth device.

## Prerequisites
On Debian based machines:
```
apt-get install python3-pip python3-setuptools libglib2.0-dev build-essential
```

Install Python dependencies:
```
pip3 install requirements.txt
```

## Discovering and setting up your devices
1 .-
2 .-

## How to install
1 .- Clone the repository
2 .- Install "requirements.txt
2 .- Move the project folder to your prefered location
3 .- Edit the "src/bletracker.service" and set the right paths to "WorkingDirectory" and "ExecStart"
4 .- Adjust your settings in "config.yaml"
5 .- Install the service
    cp src/bletracker.service /etc/systemd/system/
    systemctl enable bletracker
6 .- You're ready to go
    systemctl 
