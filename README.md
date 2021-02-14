## BLE Tracker

This project was made to reuse RPI/OSMC devices as BLE tracker, but it can work on any Linux machine with a Bluetooth device.

## Description

multiroom + hass + kalman filter

## Prerequisites
- On Debian based machines:
```
apt-get install python3-pip python3-setuptools python3-dev libglib2.0-dev build-essential git
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

## General setup
Before running the BLE tracker, you need to configure some settings in `config.yaml`.

 - `scan_period`: BLE scanning interval
 - `mqtt.name`: Client ID to use when sending MQTT messages
 - `mqtt.host`: MQTT Server
 - `mqtt.port`: MQTT Port
 - `mqtt.username`: MQTT Username
 - `mqtt.password`: MQTT Password
 - `mqtt.topic`: MQTT Topic used by this tracker device. **Note**: Each tracker device must use a different topic.
 - `mqtt.qos`: MQTT QoS (see https://www.eclipse.org/paho/files/mqttdoc/MQTTClient/html/qos.html)
 - `mqtt.keepalive`: MQTT Keepalive. If no data has been transfered with the MQTT server after that value, client sends a heartbeat to the server.
 - `messages.include_location`: Boolean to specify whether include the name of the estimated location of the device in the MQTT message or not.
 - `messages.include_rssi`: Boolean to specify whether include the RSSI in the MQTT message or not.
 
## Including location names
You can send the name of the location where your device is at, by configuring the `locations` ranges.
By default, location names are not sent to the MQTT server, but you can include them by setting the boolean setting `messages.include_location` in `config.yaml`.

### Defining locations
Locations are defined depending on the distance between the tracker device and the tracked device.
To add a new location, [set up the tracked device](#Discovering-and-setting-up-your-devices)  in the `config.yaml` file.

## Discovering and setting up your devices
### Distance calculation
There are lot of different ways to **estimate** the distance to the BLE device, here we're using the formula:

```
distance = 10 ^ ( (MR — RSSI) / (10 * N) )
```

For the software to be able to calculate the distance to your device, you need to provide three parameters per each BLE device:
1. **RSSI**: Received signal strength indicator from the device to track
2. **MR**: RSSI at 1 meter away
2. **N**: Constant (depending on environment conditions)

### Discovering and adjustment

**IMPORTANT**: Before running any scan, place the BLE device 1 meter away from the BLE scanner device.

To discover devices as well as calculate the "**MR**" and the "**N**" constant, run the script with the following arguments:

```
python3 src/tracker.py --scan --device [device-mac-here]
```

***Note**: To see all the devices in range, remove the "--device [device-mac-here]" argument

Let that scan run for a while, and once the "distance" variable is close to 1 meter and "stable" between different samples, stop the scan by pressing "CTRL+C" and write down the "**MR**" and "**N**" variables.

Sample output:
```
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-0.1671, N=4.90251674, Distance=23.08
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-75 dB, MR=-25.3183, N=4.15764916, Distance=15.67
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-77 dB, MR=-38.4631, N=3.67363437, Distance=11.19
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-77 dB, MR=-46.3992, N=3.32897478, Distance=8.30
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-72 dB, MR=-50.8587, N=2.91815640, Distance=5.30
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-77 dB, MR=-54.8311, N=2.96278122, Distance=5.60
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-76 dB, MR=-57.7031, N=2.79462608, Distance=4.52
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-58.8496, N=2.35396926, Distance=2.22
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-76 dB, MR=-60.8000, N=2.66012685, Distance=3.73
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-72 dB, MR=-61.9886, N=2.43478816, Distance=2.58
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-63.3710, N=2.15760607, Distance=1.47
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-72 dB, MR=-64.1557, N=2.34067466, Distance=2.16
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-64.4047, N=2.11271405, Distance=1.33
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-77 dB, MR=-65.4715, N=2.50067683, Distance=2.89
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-76 dB, MR=-66.3382, N=2.41960843, Distance=2.51
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-69.6263, N=2.11405924, Distance=0.75
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-71 dB, MR=-69.5530, N=2.06284109, Distance=1.18
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-71 dB, MR=-69.6518, N=2.05855109, Distance=1.16
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-69.4929, N=2.10826675, Distance=0.76
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-69.3228, N=2.10087613, Distance=0.78
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-67 dB, MR=-69.1642, N=2.09399012, Distance=0.79
ca:fe:ca:fe:ca:fe (BLE Device), RSSI=-70 dB, MR=-69.6756, N=2.01408935, Distance=1.04
```

In this case, let's write down:
 - **MR**: -69.6756
 - **N**: 2.01408935


### Device set up

In order to track the device, edit the file `config.yaml` and add the following under the `devices` section:

```
devices:
  - mac: ca:fe:ca:fe:ca:fe
    name: ble tag 1
    measured_rssi: -69.6756
    n: 2.01408935
    timeout: 0
    status_off: not_home
```

## How to install
1. Move the project folder to your prefered location
2. Edit the `src/bletracker.service` and set the right paths to `WorkingDirectory` and `ExecStart`
3. Adjust your settings in `config.yaml`
4. Install the service
```
cp src/bletracker.service /etc/systemd/system/
systemctl enable bletracker
```
5. You're ready to go
```
systemctl start bletracker
```
