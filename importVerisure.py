#!/usr/bin/python3

import argparse
import arrow
import configparser
import logging
import json
import os.path
import urllib.request 
import verisure

# Version 0.1
# Author: Jan De Luyck (jan@kcore.org) 
#
# This script depends on the verisure module by Per Sandström, 
# which you can find at https://github.com/persandstrom/python-verisure
#
# Notes: if you want additional sensors to be added, supply me with the 
# output of 
#	vsure 'user' 'password' overview 

################################
# Device config
# Create a dummy hardware device, and add per item you want in 
# Domoticz a Virtual Sensor
# - Temperature + Humidity: smoke detectors
# - Temperature: Siren
# - Switch (on/off): door/window locks (on/off), ethernet status 
# - Switch (selector): arm state, add off/arm stay / arm away
# - Custom Sensor (X Axis: SMS count): SMS
#
# Add the Verisure identifiers _and_ the device ID's (which you can find on 
# the devices view) to vsure.ini (or your own ini file)
# Please keep the identifiers 'sms count' and 'arm state' for the smscount and 
# alarm state respectively

#################################
def parseArgs():
	parser = argparse.ArgumentParser(description = 'Import Verisure information into Domoticz', prog='importVerisure.py')
	parser.add_argument('-l', '--log', dest='logLevel',type=str, choices=['info', 'warning', 'error', 'debug'], help='Specifies the loglevel to be used')
	parser.add_argument('-c', '--config', dest='configFile', default='vsure.ini', type=str, help='Name of the configuration file to use (default: %(default)s')

	results = parser.parse_args()
							
	return vars(results)

def parseConfig(configFile):
	config = configparser.ConfigParser()
	
	if not os.path.isfile(configFile):
		logging.debug('Config file %s does not exist, creating dummy', configFile)
		# create a 'new' config file and write it
		config['domoticz'] = { 'protocol' : 'http', 'host':'localhost', 'port':'8080'}
		config['verisure'] = { 'username':'', 'password':''}
		config['global'] = { 'loglevel':'warning', 'timezone':'local'}
		config['sensorindex'] = { 'sms count':'XX', 'arm state':'XX', 'AAAA BBBB':'XX'}
		
		with open(configFile, 'w') as file:
			config.write(file)			
		
		print ("A default (empty) config file was written as %s. Please review and re-run this script.", configFile)
		exit (1)
	else:
		config.read(configFile)
		
		return config
		
def callDomoticz(url):
	logging.debug ('** Entered CallDomoticz(%s) **', url)

	response = urllib.request.urlopen(url)
	httpOutput = response.read().decode('utf-8')
	output = json.loads(httpOutput)
	logging.debug ('Output: %s', output)

	if output['status'] == 'OK':
		if 'result' in output:
			returnValue = output['result'][0]
		else:
			returnValue = output
	else:
		returnValue = -1
		logging.error ('ERROR: error occurred querying Domoticz! Full output available in debug.')

	return returnValue

def getLastDomoticzUpdatedTimestamp(deviceIndex, timeZone):
	global domoticzUrl
	logging.debug ('** Entered getLastDomoticzUpdatedTimestamp(%s) **', deviceIndex)
	output = callDomoticz(domoticzUrl + 'type=devices&rid=' + str(deviceIndex))
	if output != -1:
		returnValue = arrow.get(arrow.get(output['LastUpdate']).naive, timeZone).timestamp
	else:
		returnValue = output

	logging.debug('Return value: %s', str(returnValue))

	return returnValue

def getVerisureInfo(verisureUser, verisurePw):
	logging.debug ('** Entered getVerisureInfo(username,password) **')
	# Connect to Verisure and get all the data
	verisureSession = verisure.Session(verisureUser, verisurePw);
	verisureSession.login()
	verisureOverview = verisureSession.get_overview()
	verisureSession.logout()

	logging.debug ('Verisure output:')
	logging.debug ('************************')
	logging.debug (verisureOverview)
	logging.debug ('************************')
	
	return verisureOverview

def processUpdates(deviceType, sensorIdx, deviceLastUpdated, device, timeZone):	
	global config, domoticzUrl
	
	if 'deviceLabel' not in device:
		device['deviceLabel'] = deviceType.upper()

	logging.info ('Now processing device %s (sensorIdx %s)', device['deviceLabel'], sensorIdx)
	
	# get last updated time in Domoticz
	lastUpdatedDomoticz = getLastDomoticzUpdatedTimestamp(sensorIdx,config['global']['timezone'])
	
	if lastUpdatedDomoticz != -1:
		logging.info (' - Last Updated in Domoticz: %s', arrow.get(lastUpdatedDomoticz).naive)	
		
		# Last updated on Verisure
		lastUpdatedVerisure = arrow.get(deviceLastUpdated).timestamp
		logging.info (' - Last updated in Verisure: %s', arrow.get(lastUpdatedVerisure).naive)
		
		if lastUpdatedVerisure > lastUpdatedDomoticz:
			# Climate devices
			if deviceType == 'climate':
				logging.info (' - Updating temperature to %s', str(device['temperature']))				
				requestUrl = 'type=command&param=udevice&idx=' + sensorIdx + '&nvalue=0&svalue=' + str(device['temperature'])

				if 'humidity' in device:
					logging.info (' - Updating humidity to %s', str(device['humidity']))
					requestUrl += ';' + str(device['humidity']) + ';0'
				
			elif deviceType == 'doorwindow':
				# doorWindow locks
				if device['state'] == 'CLOSE':
					switchState = 'Off'
				elif device['state'] == 'OPEN':
					switchState = 'On'

				logging.info (' - Updating switch status to %s', switchState)
				requestUrl = 'type=command&param=switchlight&idx=' + sensorIdx + '&switchcmd=' + switchState
				
			elif deviceType == 'smscount':
				# SMS Count
				logging.info (' - Updating SMS count to %s', device['totalSmsCount'])
				requestUrl = 'type=command&param=udevice&idx=' + sensorIdx + '&nvalue=0&svalue=' + str(device['totalSmsCount'])
				
			elif deviceType == 'armstate':
				# Alarm Arm status
				if device['statusType'] == "DISARMED":
					alarmState = '0'
				elif device['statusType'] == "ARMED_HOME":
					alarmState = '10'
				elif device['statusType'] == "ARMED_AWAY":
					alarmStateu = '20'
					
				logging.info (' - Updating alarm state to %s', alarmState)
				requestUrl = 'type=command&param=switchlight&idx=' + sensorIdx + '&switchcmd=Set%20Level&level=' + alarmState

			elif deviceType == 'ethstate':
				# Ethernet status
				if device['latestEthernetTestResult'] == True:
					ethernetState = 'On'
				else:
					ethernetState = 'Off'
				
				logging.info (' - Updating ethernet state to %s', ethernetState)
				requestUrl = 'type=command&param=switchlight&idx=' + sensorIdx + '&switchcmd=' + ethernetState
				
			else:
				logging.error ('ERROR: Unknown device type!')
				requestUrl = None
				
			if requestUrl != None:
				output = callDomoticz(domoticzUrl + requestUrl)

				if output == -1:
					logging.error ('ERROR: Update not sent to Domoticz for device %s!', sensorIdx)
				else:
					logging.info (' - Update sent successfully to Domoticz')
		else:
			logging.info (' - Not updating Domoticz')
	else:
		logging.error ('ERROR: something went wrong querying Domoticz!')


def main():
	# Parse command line
	arguments = parseArgs()

	# Read config
	config = parseConfig(arguments["configFile"])

	# Overwrite loglevel, it can be passed on command line
	if arguments['logLevel'] != None:
		config['global']['loglevel'] = str(arguments['logLevel'])

	# Switch default log level
	logging.basicConfig(format='%(asctime)s %(message)s', level=getattr(logging, config['global']['loglevel'].upper()))

	# Construct Domoticz url
	domoticzUrl = config['domoticz']['protocol'] +  '://' + config['domoticz']['host'] + ':' + config['domoticz']['port'] + '/json.htm?'
	
	verisureOverview = getVerisureInfo(config['verisure']['username'], config['verisure']['password'])
	
	# Process climateValues
	for device in verisureOverview['climateValues']:
		if device['deviceLabel'] in config['sensorindex']:
			processUpdates('climate', config['sensorindex'][device['deviceLabel']], device['time'], device)
	
	# Process DoorWindowDevices
	for device in verisureOverview['doorWindow']['doorWindowDevice']:
		if device['deviceLabel'] in config['sensorindex']:
			processUpdates('doorwindow', config['sensorindex'][device['deviceLabel']], device['reportTime'], device)

	# Process SMS
	processUpdates('smscount', config['sensorindex']['sms count'], arrow.now(), verisureOverview)
	
	# Process Alarm State
	processUpdates('armstate', config['sensorindex']['arm state'], verisureOverview['armState']['date'], verisureOverview['armState'])

	# Process Ethernet State
	processUpdates('ethstate', config['sensorindex'][verisureOverview['latestEthernetStatus']['deviceLabel']], verisureOverview['latestEthernetStatus']['testDate'], verisureOverview['latestEthernetStatus'])


# Execute script
if __name__ == '__main__':
	main()
