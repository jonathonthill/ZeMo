#!/usr/bin/python3.4

import RPi.GPIO as GPIO
import serial # Required for communication with boards
import smtplib, email
import socket, struct, fcntl
import time
from email.mime.text import MIMEText
import yaml
import os, sys, re
import requests
from i2c import AtlasI2C
import csv

class Sensors(object):
    # Initializes variables to zero or empty strings
    units = "";
    highRange = 0;
    lowRange = 0;
    probe = 0;
    fileName = "";
    pinZero = 0;
    pinOne = 0;
    i2cAddress = 0;
    recipients = "";
    probeType = "";
    url = "";
    values = "";
    
    # Upload values
    mimeType = 'multipart/form-data'

    # Creates Sensor class objects
    def __init__(self, name_in, units_in, highRange_in, lowRange_in, fileName_in, probe_in, i2cAddress_in, 
                 recipients_in, daysToKeep_in, readsPerDay_in, sensorTag_in, probeType_in, url_in, values_in):
        self.name = name_in
        self.units = units_in
        self.highRange = highRange_in
        self.lowRange = lowRange_in
        self.probe = probe_in
        self.fileName = fileName_in
        self.i2cAddress = i2cAddress_in   
        self.recipients = recipients_in
        self.daysToKeep = daysToKeep_in
        self.readsPerDay = readsPerDay_in
        self.i2sensor = AtlasI2C()
        self.currRead = "NULL"
        self.sensorTag = sensorTag_in
        self.probeType = probeType_in
        self.url = url_in
        self.values = values_in
        if i2cAddress_in != -1:
            self.i2sensor.set_i2c_address(self.i2cAddress)
            if self.name == "Cond":
                self.setProbeType("K," + str(self.probeType))

    # Only reads sensor data, doesn't write to file
    def getRead(self):
        if self.i2cAddress != -1:
            maxTries = 3
            line = ""
            for i in range (0, maxTries):
                self.i2sensor.set_i2c_address(self.i2cAddress)
                data = self.i2sensor.query('R')
                if data != "":
                    read2 = float(data.split(",")[0])
                    retRead = round(read2, 1)
                    data = str(retRead)
                    return data
            return data

	# Take reads and write to file
    def takeRead(self):

        if(self.i2cAddress != -1):
            maxTries = 10
            reads = []
            reads2 = []	 
            avgRead = 0
            try:
                for i in range(0, maxTries):
                    t = int(time.time())
                    try:
                        self.i2sensor.set_i2c_address(self.i2cAddress)
                        read = self.getRead()
                        read2 = float(read.split(",")[0])
                        if(read2 != -1 and read2 != 0):
                            reads.append(float(round(read2, 1)))
                            reads2.append(str(round(read2, 1)))
                    except Exception as y:
                        errorstring = ": Error: %s" % str(y)
                        print(errorstring)
                        try:
                          self.i2sensor.set_i2c_address(self.i2cAddress)
                          read = self.getRead()
                          read2 = read.split(",")[0]
                          if(read2 != -1 and read2 != 0):
                              reads.append(float(round(read2, 1)))
                              reads2.append(str(round(read2, 1)))
                        except Exception as y:
                            errorstring = ": Error: %s" % str(y)
                            print(errorstring)
                if(sum(reads) != 0):
                    if len(reads) > 2:
                        try:
                            #Does a trimmed reading
                            highestRead = max(reads)
                            lowestRead = min(reads)
                            print(highestRead)
                            print(lowestRead)
                            reads.remove(max(reads))
                            reads.remove(min(reads))
                        except:
                            print("Failed to trim readings")
                    avgRead = float(sum(reads))/len(reads)
                #Emails all the reads if out of range, including the ones that were trimmed
                self.checkAlarms(avgRead, reads2)
                outFile = open(self.fileName, 'a')
                if self.units != None:
                    reads.append(str(self.probe) + ": " + str(round(avgRead, 1)) + " " + self.units)
                else:
                    reads.append(str(self.probe) + ": " + str(round(avgRead, 1)))
                outFile.write(str(t * 1000) + "," + str(self.lowRange) + ";" + str(round(avgRead, 1)) + ";" + str(self.highRange))
                outFile.write("\n")
                outFile.close()
                files = {'postedFile': (self.fileName, open(self.fileName, 'rb'), self.mimeType)}
                r = requests.post(self.url, data = self.values, files = files)
                return_data = "\t".join(str(reads))
                self.limitLines()
            except Exception as e:
                t = int(time.time())
                errorstring = time.ctime(t) + ": Error: %s" % str(e)
                print(errorstring)        
            return(reads)

    def calibrateSensor(self, query):
        maxTries = 3
        for i in range (0, maxTries):
            self.i2sensor.set_i2c_address(self.i2cAddress)
            data = self.i2sensor.query(query)
            if data == "Success":
                return data
            if (maxTries - 1) == i:
                return data

    def setProbeType(self, query):
        maxTries = 3
        for i in range (0, maxTries):
            self.i2sensor.set_i2c_address(self.i2cAddress)
            data = self.i2sensor.query(query)

    # Limits file size to 1 MB
    def limitFileSize(self):
        limitSize = 1
        csv.field_size_limit(limitSize)
    
    # Limits the number of lines recorded in the csv file
    def limitLines(self):
        f = open(self.fileName)
        test = f.readlines()
        if self.readsPerDay > 0 and self.daysToKeep > 0:
            lines = (int(self.readsPerDay) * int(self.daysToKeep))
            if len(test) > lines:
                deleteLines = len(test) - lines
                del test[:deleteLines]
                testout = open(self.fileName, "w")
                testout.writelines(test)
                testout.close()
        f.close()

	# Checks the values and opens notify() if values are out of range, the ooR occurs here
    def checkAlarms(self, avgRead, reads):
        if avgRead > float(self.highRange) or avgRead < float(self.lowRange):
            self.notify(reads)
            return

    # Tests to make sure probes are working
    def testProbes(self):
        self.getRead()

	# Sends notification email if values are out of range
    def notify(self, reads):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockfd = sock.fileno()
            SIOCGIFADDR = 0x8915
            #TODO add email info here
            SMTP_SERVER = 'smtp.gmail.com'
            SMTP_PORT = 587
            SMTP_USERNAME = "username" #email username
            SMTP_PASSWORD = "password" #your email password
            SMTP_FROM = example@email.com #sends from this email address
            print("send email")

            for address in self.recipients:
                SMTP_TO = address

                mailer = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                mailer.ehlo()
                mailer.starttls()
                mailer.login(SMTP_USERNAME, SMTP_PASSWORD)

                msg = MIMEText("The fish system is out of range. Current values for " + str(self.name) + " are:\n" + " \n".join(reads))
                msg['Subject'] = 'Fish Parameters Out of Range'
                msg['To'] = SMTP_TO
                msg['From'] = SMTP_FROM

                mailer.send_message(msg)
                mailer.quit()
        except Exception as e:
            print("Did not send email")

    # Add an email to the list
    def addEmail(self):
        emailToAdd = ""
        emailToAdd = input("Add Email: ")
        newEmailList = []
        inList = False
        with open("/home/pi/FishCode/EmailList.txt", "r") as f:
            for line in f:
                cleanedLine = line.strip()
                if cleanedLine:
                    if cleanedLine == emailToAdd:
                        print("Email already in list.")
                        inList = True
                    else:
                        newEmailList.append(cleanedLine)
        if(inList == False):
            emailFile = open("/home/pi/FishCode/EmailList.txt", "a")
            emailFile.write("\n" + emailToAdd)
            newEmailList.append(emailToAdd)
            print(emailToAdd + " added to list")    
        emailFile.close()
        self.updateEmailList(newEmailList)
 
    # Remove an email from the list
    def removeEmail(self):
        emailToRemove = ""
        emailToRemove = input("Remove Email: ")
        newEmailList = []
        inList = False
        with open("/home/pi/FishCode/EmailList.txt", "r") as f:
            for line in f:
                cleanedLine = line.strip()
                if cleanedLine:
                    if cleanedLine == emailToRemove:
                        inList = True
                    else:
                        newEmailList.append(cleanedLine)
        if(inList == True):
            emailFile = open("/home/pi/FishCode/EmailList.txt","w")
            for EmailList in newEmailList:
                emailFile.write("\n" + EmailList)
            print(emailToRemove + " was removed.")
        else:
            print("Email not found in list.")
        emailFile.close()
        self.updateEmailList(newEmailList)

    # Updates object's recipients
    def updateEmailList(self, newEmailList):
        self.recipients = newEmailList