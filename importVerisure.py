#!/usr/bin/python3

# Version 0.4
# Author: Jan De Luyck (jan@kcore.org) 
# Licensed under the GPL v3.0
# URL: https://github.com/jdeluyck/verisure-domoticz/

import arrow
import logging
import json
import urllib.request 
import verisure

from verisure_domoticz import parseArgs, parseConfig

#################################
        
def callDomoticz(url):
    logging.debug ('** Entered CallDomoticz(%s) **', url)

    try:
        response = urllib.request.urlopen(url)
        httpOutput = response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
            logging.error ('HTTP Error encountered connecting to URL %s', url)
            logging.error('%s', str(e.reason))
            exit(1)
    except urllib.error.URLError as e:
            logging.error('URL Error encountered connecting to URL %s', url)
            logging.error('%s', str(e.reason))
            exit (1)
    except httplib.HTTPException as e:
            logging.error ('HTTP Exception encountered connecting to URL %s', url)
            logging.error('%s', str(e.reason))
            exit(1)
    except Exception:
            import traceback
            logging.error('Other error encountered connecting to URL %s', url)
            logging.error(traceback.format_exc())
            exit(1)

    output = json.loads(httpOutput)
    logging.debug ('Output: %s', output)

    if output['status'] == 'OK':
        if 'result' in output:
            returnValue = output['result'][0]
        else:
            returnValue = output
    else:
        returnValue = -1
        logging.error ('Error: error occurred querying Domoticz! Full output available in debug.')

    return returnValue

def getLastDomoticzUpdatedTimestamp(deviceIndex, timeZone):
    global domoticzUrl
    logging.debug ('** Entered getLastDomoticzUpdatedTimestamp(%s) **', deviceIndex)
    output = callDomoticz(domoticzUrl + 'type=devices&rid=' + str(deviceIndex))
    if output != -1:
        if 'LastUpdate' in output:
            returnValue = arrow.get(arrow.get(output['LastUpdate']).naive, timeZone).timestamp
        else:
            logging.error ('Warning: device %s does not exist in Domoticz! Please check configuration!', str(deviceIndex))
            returnValue = -1
    else:
        returnValue = output

    logging.debug('Return value: %s', str(returnValue))

    return returnValue

def getVerisureInfo(verisureUser, verisurePw):
    logging.debug ('** Entered getVerisureInfo(username,password) **')
    # Connect to Verisure and get all the data
    verisureSession = verisure.Session(verisureUser, verisurePw);
    try:
        verisureSession.login()
    except:
        logging.error ('Error when logging into Verisure. Please check your username and password!')
        exit (1)

    try:
        verisureOverview = verisureSession.get_overview()
    except:
        logging.error ('Error when getting the Verisure overview!')
        exit (1)

    try:
        verisureSession.logout()
    except:
        logging.error ('Error when logging out of Verisure. Please check your username and password!')
        exit (1)

    logging.debug ('Verisure output:')
    logging.debug ('************************')
    logging.debug (verisureOverview)
    logging.debug ('************************')
    
    return verisureOverview

def processUpdates(deviceType, sensorIdx, deviceLastUpdated, device):    
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
                if device['statusType'] == 'DISARMED':
                    alarmState = '0'
                elif device['statusType'] == 'ARMED_HOME':
                    alarmState = '10'
                elif device['statusType'] == 'ARMED_AWAY':
                    alarmState = '20'
                    
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

            elif deviceType == 'switchstate':
                # Control/Smart switch state
                logging.info (' - Updating switch state to %s', device['currentState'])
                requestUrl = '&type=command&param=switchlight&idx=' + sensorIdx + '&switchcmd=' + str(device['currentState'])
                
            else:
                logging.error ('Error: Unknown device type!')
                requestUrl = None
                
            if requestUrl != None:
                output = callDomoticz(domoticzUrl + requestUrl)

                if output == -1:
                    logging.error ('Error: Update not sent to Domoticz for device %s!', sensorIdx)
                else:
                    logging.info (' - Update sent successfully to Domoticz')
        else:
            logging.info (' - Not updating Domoticz')
    else:
        logging.error ('Error: No valid response returned by Domoticz. Please check configuration!')


def main():
    global domoticzUrl, config
    # Parse command line
    arguments = parseArgs('importVerisure.py', '0.4')

    # Read config
    config = parseConfig(arguments['configFile'])

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
    
    # Process Switch State
    for device in zip(verisureOverview['smartplugs'], verisureOverview['controlplugs']):
        processUpdates('switchstate', config['sensorindex'][device['deviceLabel']], arrow.now(), device)


# Execute script
if __name__ == '__main__':
    main()
