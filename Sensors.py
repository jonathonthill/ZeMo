#!/usr/bin/python3.4

import RPi.GPIO as GPIO
import serial # Required for communication with boards
import socket, struct, fcntl
import time
import Emailer
from Emailer import *
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
    emailer = Emailer()
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
                file2 = self.fileName[:-4]
                outFileLog = open(file2 + "_log.csv", 'a')
                if self.units != None:
                    reads.append(str(self.probe) + ": " + str(round(avgRead, 1)) + " " + self.units)
                else:
                    reads.append(str(self.probe) + ": " + str(round(avgRead, 1)))
                outFile.write(str(t * 1000) + "," + str(self.lowRange) + ";" + str(round(avgRead, 1)) + ";" + str(self.highRange))
                outFile.write("\n")
                outFile.close()
                outFileLog.write(str(t * 1000) + "," + str(self.lowRange) + ";" + str(round(avgRead, 1)) + ";" + str(self.highRange))
                outFileLog.write("\n")
                outFileLog.close()
                #TODO edit this to allow the posting of data, work with Josh on this
                files = {'postedFile': (self.fileName, open(self.fileName, 'rb'), self.mimeType)}
                r = requests.post(self.url, data = self.values)#, files = files)
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
            daysKept = int(self.daysToKeep)
            # if limiting to 6 months regardless of amount reads per day, add next two lines:
            #if daysKept > 183:
            #    daysKept = 183
            lines = (int(self.readsPerDay) * daysKept)
            # Limits file to the server size of 6 months worth of data
            if lines > 4400:
                lines = 4400
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
            self.emailer.sendEmail(reads, self.recipients, 
                                   "The fish system is out of range. Current values for " + str(self.name) + " are:\n",
                                   'Fish Parameters Out of Range')
            #self.notify(reads)
            return

    # Tests to make sure probes are working
    def testProbes(self):
        self.getRead()


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