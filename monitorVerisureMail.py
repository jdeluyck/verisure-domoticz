#!/usr/bin/python3

# Version 0.4
# Author: Jan De Luyck (jan@kcore.org) 
# Licensed under the GPL v3.0
# URL: https://github.com/jdeluyck/verisure-domoticz/

import imapclient   
import logging
import socket

import importVerisure
from verisure_domoticz import parseArgs, parseConfig

#################################

def main():
    global domoticzUrl, config
    # Parse command line
    arguments = parseArgs('monitorVerisureMail.py', '0.4')

    # Read config
    config = parseConfig(arguments['configFile'], 'email')

    # Overwrite loglevel, it can be passed on command line
    if arguments['logLevel'] != None:
        config['global']['loglevel'] = str(arguments['logLevel'])

    # Switch default log level
    logging.basicConfig(format='%(asctime)s %(message)s', level=getattr(logging, config['global']['loglevel'].upper()))

    try:
        logging.debug('IMAP: Connecting to %s:%s, SSL: %s', config['email']['host'], config['email']['port'], config['email']['ssl'])

        try:
            imapHandler = imapclient.IMAPClient(host = config['email']['host'], port = config['email']['port'], ssl = config['email']['ssl'], timeout = 15)
        except socket.gaierror:
            logging.error('Error encountered trying to connect to %s:%s. Please check host and port!', config['email']['host'],config['email']['port'])
            exit(1)
        except socket.timeout:
            logging.error('Timeout occurred when connecting to %s:%s. Please check host and port!', config['email']['host'],config['email']['port'])
            exit (1)
        
        
        if config['global']['loglevel'].upper() == "DEBUG":
            imapHandler.debug = True

        # Try to start an SSL context if starttls is available
        if config['email']['ssl'] != True and imapHandler.has_capability('STARTTLS'):
            logging.debug('IMAP: STARTTLS is supported, activating...')
            try:
                imapHandler.starttls()
            except imapclient.IMAPClient.Error as e:
                logging.error('Error encountered issuing STARTTLS: %s', e)
                exit(1)
        
        logging.debug('IMAP: Checking for IDLE...')
        if not imapHandler.has_capability('IDLE'):
            logging.error('Error: email server %s doesn\'t advertise capability IDLE! Cannot continue...', config['email']['host'])
            exit(1)
        
        logging.debug('IMAP: Authenticating with username %s', config['email']['username'])
        try:
            imapHandler.login(config['email']['username'], config['email']['password'])
        except imapclient.IMAPClient.Error as e:
            logging.error('Error encountered logging into IMAP server. Please check your username and password!')
            exit(1)

        # Select the correct folder
        logging.debug('IMAP: selecting folder %s', config['email']['folder'])
        try:
            imapHandler.select_folder(config['email']['folder'], readonly=True)
        except imapclient.IMAPClient.Error as e:
            logging.error('Error encountered selecting folder \'%s\'. Does it exist?', config['email']['folder'])
            imapHandler.logout()
            exit(1)

        # Idle away!
        logging.debug('IMAP: setting mailbox to IDLE mode...')
        try:
            imapHandler.idle()

            while True:
                logging.debug('IMAP: Calling idle_check()')
                imapHandler.idle_check()
                logging.debug('IMAP: idle_check() returned, triggering import from Verisure...')
                importVerisure.main()
                
        except imapclient.IMAPClient.Error as e:
            logging.error('Error encountered in IDLE loop: %s', e)
            exit(1)
            
    except SystemExit:
        pass
    except imapclient.IMAPClient.Error as e:
        print (e)
    except:
        print ("error handler!")
        imapHandler.idle_done()
        imapHandler.logout()        

# Execute script
if __name__ == '__main__':
    main()
