# verisure-domoticz
Scripts to query Verisure and pump the data into Domoticz

## License
These scripts are licensed under the GPL 3.0. You can find the full license in the [LICENSE](https://github.com/jdeluyck/verisure-domoticz/LICENSE) file.

## Credits
These scripts wouldn't exist without [verisure module](https://github.com/persandstrom/python-verisure) by Per Sandström.

## importVerisure.py
This script is designed to log into the Verisure API, and get out all the information of the system at that time.
It then processes the devices specified in `vsure.ini` (see below) to see which ones it needs to upload into Domoticz.

## monitorVerisureMail.py
This script is designed to open an imap idle connection to a mailbox folder, to monitor for Verisure events. This allows us to react quicker to specific events, than every X minutes (as specified by the cron job). 

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

I don't own any other devices (smart plugs, camera's, ...) in my own setup, so I'm not 100% sure on what sensor information I need. Feel free to [add an issue](https://github.com/jdeluyck/verisure-domoticz/issues/new) with additional information. Ideally add the output of `vsure youruser yourpass overview`, but remove any sensitive info (like actual component identifiers).

You'll also need the following sensors (mandatory):
  * SMS Counter: Custom Sensor, X Axis: SMS Count
  * Alarm status: Switch (selector type) with three states: 
    * 0: Off
    * 10: Armed Home
    * 20: Armed Away

#### vsure.ini
The configuration is handled through an ini-style config file called `vsure.ini` (by default, you can specify any other using command line parameters)

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

[email]
host =
port = 
ssl = 
folder = 
username = 
password = 
```

  * The `domoticz` section contains parameters needed to connect to your Domoticz instance.
  * the `verisure` section specifies your username (email) and password to get into verisure.
  * `global` contains the timezone your domoticz is running in (specifying local here takes the time from /etc/timezone), and the default loglevel you want. You can choose from DEBUG, INFO, WARNING, ERROR and CRITICAL. Note: DEBUG will output your passwords, too!
  * `sensorindex` is the block where you need to match up the serial ID if your Verisure components with the sensor index in Domoticz. Say your device has an identifier of JC2B XYZB, and the device identifier in Domoticz is 10, you'll need to add a line reading `JC2B XYZB = 10`.
    You also need to keep the lines `sms count = xx` and `arm state = xx`, and specify the sensor index from Domoticz. These reflect the SMS counter and the alarm armed status.
  * The `email` section contains the configuration parameters to connect to your email provider. See below for more info.

#### Email configuration
In case you want to use the mail polling script `monitorVerisureMail.py`, you'll need to add a user in the Verisure configuration and configure it to receive mails on Alarm events. You'll also need to add a filter so that all those mails are filtered into a specific subfolder.
Then supply the necessary email server info in the `vsure.ini` configuration file.
  * `host`: your email IMAP server. _POP3 is not supported at this time_
  * `port`: the port to connect to. This is usually related directly to the parameter `ssl` (encryption)
  * `ssl`: wether or not to activate SSL from the get-go. The script will try to use STARTTLS if available.
  * `folder`: the folder in which we will receive mails from Verisure. I decided to not check which mails we get in this folder, but just to trigger the `importVerisure.py` script. This works around several issues, including language, formatting, ...

### Command line parameters
The easiest way to get them is to ask for them ;)
```
$ ./importVerisure.py -h
usage: importVerisure.py [-h] [-v] [-l {info,warning,error,debug,critical}]
                         [-c CONFIGFILE]

Import Verisure information into Domoticz

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -l {info,warning,error,debug,critical}, --log {info,warning,error,debug,critical}
                        Specifies the loglevel to be used
  -c CONFIGFILE, --config CONFIGFILE
                        Name of the configuration file to use (default:
                        vsure.ini
```

### Scheduling importVerisure.py through cron
Easy as
```
*/10 * * * * /home/domoticz/importVerisure.py
```

I don't know what the call limit is on the API, but I've not gotten any errors with a 10 minute interval.

### Using monitorVerisureMail.py
Since I'm already running Domoticz through `systemd`, it was only logical to create a systemd unit file for this. You can find it [here](https://github.com/jdeluyck/verisure-domoticz/monitorVerisureMail.service)

You can copy it to `/etc/systemd/system`, install it using `systemctl enable monitorVerisureMail.py` and start it with `systemctl start monitorVerisureMail.py`. You'll probably have to modify it to your installation.

