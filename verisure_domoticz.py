# Common functions for verisure-domoticz scripts
# Author: Jan De Luyck (jan@kcore.org) 
# Licensed under the GPL v3.0
# URL: https://github.com/jdeluyck/verisure-domoticz/

#################################

import argparse
import configparser
import logging
import os.path

def parseArgs(progName, progVersion):
    parser = argparse.ArgumentParser(description = 'Import Verisure information into Domoticz', prog=progName)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + progVersion)
    parser.add_argument('-l', '--log', dest='logLevel',type=str, choices=['info', 'warning', 'error', 'debug', 'critical'], help='Specifies the loglevel to be used')
    parser.add_argument('-c', '--config', dest='configFile', default='vsure.ini', type=str, help='Name of the configuration file to use (default: %(default)s')

    results = parser.parse_args()
                            
    return vars(results)

def parseConfig(configFile, additionalConfigSection=''):
    config = configparser.ConfigParser()
    
    if not os.path.isfile(configFile):
        logging.debug('Config file %s does not exist, creating dummy', configFile)
        # create a 'new' config file and write it
        config['domoticz'] = { 'protocol' : 'http', 'host':'localhost', 'port':'8080'}
        config['verisure'] = { 'username':'', 'password':''}
        config['global'] = { 'loglevel':'warning', 'timezone':'local'}
        config['email'] = { 'host':'', 'port':'567', 'ssl':'true', 'folder':'', 'username':'', 'password':''}
        config['sensorindex'] = { 'sms count':'XX', 'arm state':'XX', 'AAAA BBBB':'XX'}
        
        try:
            with open(configFile, 'w') as file:
                config.write(file)
        except IOError as e:
            logging.error ('Error when writing the default (empty) config file %s: %s', configFile, str(e.reason))
        else:
            logging.warning ('A default (empty) config file was written as %s. Please review and re-run this script.', configFile)

        exit (1)
    else:
        config.read(configFile)

        # Verify the basics of the config
        requiredKeys = {}
        requiredKeys['domoticz'] = {'protocol', 'host', 'port'}
        requiredKeys['verisure'] = {'username', 'password'}
        requiredKeys['global'] = {'loglevel', 'timezone'}
        requiredKeys['sensorindex'] = {'sms count', 'arm state'}

        if additionalConfigSection is 'email':
            requiredKeys['email'] = {'host','port','ssl','folder','username','password'}

        for section in requiredKeys:
            if not section in config:
                logging.error ('Error: section %s is missing. Please check your config file %s!', section, configFile)
                exit(1)
            else:
                for key in requiredKeys[section]:
                    if not key in config[section]:
                        logging.error ('Error: mandatory key %s is missing in section %s. Please check your config file %s!', key, section, configFile)
                        exit(1)
                    elif not config[section][key]:
                        logging.error ('Error: mandatory key %s is empty in section %s. Please check your config file %s!', key, section, configFile)
                        exit(1)
        
        # If we survive here, I guess we have a valid config.
        return config
