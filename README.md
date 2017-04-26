# verisure-domoticz
Scripts to query Verisure and pump the data into Domoticz

## License
These scripts are licensed under the GPL 3.0. You can find the full license in the LICENSE file.

## importVerisure.py
This script is designed to log into the Verisure API, and get out all the information of the system at that time.
It then processes the devices specified in `vsure.ini` (see below) to see which ones it needs to upload into Domoticz.

### Configuring
Configuration is handled through an ini-style configuration file. By default, when run the first time, the script will create a file in the current directory called `vsure.ini`.

#### Domoticz configuration
##### Hardware
In the `hardware` section, you need to add a device called `Dummy (Does nothing, use for virtual switches only)`.
Next, you need to add (using `Create virtual Sensors`) the following sensors **per device of a certain type in your Verisure installation that you want in Domoticz**
  * Smoke detector: add a Temperature + Humidity sensor
  * Siren: Temperature sensor
  * Door/window magnetic lock: Switch (on/off)
  * Ethernet status: Switch (on/off)

I don't have any other devices in my own setup right now, so I'm not 100% sure on what sensor information I need. Feel free to [add an issue](https://github.com/jdeluyck/verisure-domoticz/issues/new) with additional information!

You'll also need the following sensors (mandatory):
  * SMS Counter: Custom Sensor, X Axis: SMS Count
  * Alarm status: Switch (selector type) with three states: 
    * 0: Off
    * 10: Armed Home
    * 20: Armed Away

#### vsure.ini
The configuration is handled through an ini-style config file called vsure.ini (by default, you can specify any other using command line parameters)

The blank file written is
```
[domoticz]
port = 8080
host = localhost
protocol = http

[verisure]
password = 
username = 

[global]
loglevel = warning
timezone = local

[sensorindex]
aaaa bbbb = XX
sms count = XX
arm state = XX
```

  * The `domoticz` section contains parameters needed to connect to your Domoticz instance.
  * the `verisure` section specifies your username (email) and password to get into verisure.
  * `global` contains the timezone your domoticz is running in (specifying local here takes the time from /etc/timezone), and the default loglevel you want. You can choose from DEBUG, INFO, WARNING and ERROR.
  * `sensorindex` is the block where you need to match up the serial ID if your Verisure components with the sensor index in Domoticz.  
    Say your device has an identifier of JC2B XYZB, and the device identifier in Domoticz is 10, you'll need to add a line reading `JC2B XYZB = 10`. 

### Command line parameters


### Scheduling through cron
Easy as
```
*/10 * * * * /home/domoticz/importVerisure.py
```
I don't know what the call limit is on the API, but I've not gotten any errors with a 10-minute interval.

