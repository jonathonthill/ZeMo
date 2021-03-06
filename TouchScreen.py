#!/usr/bin/python3.4

import os
import sys
import pygame as pg
import pygame.gfxdraw
import serial # Required for communication with boards
import time # Used for timestamps, delays
import Sensors
from Sensors import *
import Emailer
from Emailer import *
import RPi.GPIO as GPIO
from datetime import datetime
import logging
import subprocess
import socket
import yaml
from threading import Thread
#from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock as lock
import Screen

# Configures parameters
CAPTION = "Current Reads"
SCREEN_SIZE = (320, 240)
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

addressList = []

cfg_file = open("/home/pi/FishCode/Configure.yaml")
cfg = yaml.load(cfg_file)

# Adds emails to a list
emailFile = open("/home/pi/FishCode/EmailList.txt", "r")
with open("/home/pi/FishCode/EmailList.txt", "r") as f:
    for line in f:
        cleanLine = line.strip()
        if cleanLine:
           addressList.append(cleanLine)
emailFile.close()

# <--------------------NOTE-------------------->
#TODO - Enter your username and authToken here:
# example - valuesCond = {'token' : '1234567abcdefg', 'metric' : 'cd.csv'}
valuesCond = {'token' : '1234567abcdefg',
    'metric' : 'cd.csv'}
valuesDO = {'token' : '1234567abcdefg',
    'metric' : 'do.csv'}
valuespH = {'token' : '1234567abcdefg',
    'metric' : 'ph.csv'}
valuesTemp = {'token' : '1234567abcdefg',
    'metric' : 'tp.csv'}

# <--------------------NOTE-------------------->
#TODO - Update your URL here:
# example - urlCond = 'https://zemoproject.org/djhill/rack1/metrics/cd' match the ending portion - /cd /ph /do /tp
urlCond = 'https://zemoproject.org/djhill/rack1/metrics/cd' #this does conductivity posting
urlpH = 'https://zemoproject.org/djhill/rack1/metrics/ph'
urlDO = 'https://zemoproject.org/djhill/rack1/metrics/do'
urlTemp = 'https://zemoproject.org/djhill/rack1/metrics/tp'

class App(object):
    def __init__(self):
        print("ZēMō Initializing")

        self.emailer = Emailer()

        try:
            self.eth0 = self.emailer.get_interface_ipaddress("eth0")
        except:
            self.eth0 = "none"
        self.wlan0 = self.emailer.get_interface_ipaddress("wlan0")

        try:
            self.wlan0 = self.emailer.get_interface_ipaddress("wlan0")
        except:
            self.wlan0 = "none"
        
        self.sensorList = []
        self.timeList = []
        self.waitTime = 1

        self.ph = Sensors("", "", 0, 0, "", 0, -1, addressList, 0, 0, "PH", "K,1.0","","")
        self.conductivity = Sensors("", "", 0, 0, "", 0, -1, addressList, 0, 0, "C", "K,1.0","","")
        self.dOxygen = Sensors("", "", 0, 0, "", 0, -1, addressList, 0, 0, "DO", "K,1.0","","")
        self.temperature = Sensors("", "", 0, 0, "", 0, -1, addressList, 0, 0, "T", "K,1.0","","")
        self.sensorList.append(self.ph)
        self.sensorList.append(self.conductivity)
        self.sensorList.append(self.dOxygen)
        self.sensorList.append(self.temperature)
        
        self.createSensors()
        try:
            self.readsPerDay = cfg["readsPerDay"]["reads"]
        except Exception as readFail:
            self.readsPerDay = 24
        try:
            self.daysToKeep = cfg["daysStored"]["days"]
        except Exception as readFail:
            self.daysToKeep = 30
        #self.ip = self.eth0 + ", " + self.wlan0
        self.viewScreen = pg.display.get_surface()
        self.background = pygame.Surface(self.viewScreen.get_size())
        # The program will exit once this is set to 'True'
        self.done = False
        self.keys = pg.key.get_pressed()
        self.color = pg.Color("black")
        # Hides Mouse, still allows click events
        pg.mouse.set_cursor((8,8),(0,0),(0,0,0,0,0,0,0,0),(0,0,0,0,0,0,0,0))
        self.topLeft = pg.Rect(5,45,152.5,92.5)
        self.btmLeftSmall = pg.Rect(5,142.5,100,92.5)
        self.middleBtnSmall = pg.Rect(110,142.5,100,92.5)
        self.btmRightSmall = pg.Rect(215,142.5,100,92.5)
        self.btmLeft = pg.Rect(5,142.5,152.5,92.5)
        self.topRight = pg.Rect(162.5,45,152.5,92.5)

        self.midLeft = pg.Rect(5,92.5,152.5,92.5)
        self.midRight = pg.Rect(162.5,92.5,152.5,92.5)
        self.centerBtn = pg.Rect(83.75,92.5,152.5,92.5)

        self.btmRight = pg.Rect(162.5,142.5,152.5,92.5)
        self.backBtn = pg.Rect(5,5,35,35)
        self.middleBtn = pg.Rect(83.75,45,152.5,92.5)
        self.settingsBtn = pg.Rect(280,5,35,35)

        self.one = pg.Rect(5,45,58,70)
        self.two = pg.Rect(68,45,58,70)
        self.three = pg.Rect(131,45,58,70)
        self.four = pg.Rect(194,45,58,70)
        self.five = pg.Rect(257,45,58,70)
        self.six = pg.Rect(5,120,58,70)
        self.seven = pg.Rect(68,120,58,70)
        self.eight = pg.Rect(131,120,58,70)
        self.nine = pg.Rect(194,120,58,70)
        self.zero = pg.Rect(257,120,58,70)
        self.period = pg.Rect(257,195,58,35)
        self.submitBtn = pg.Rect(194,195,58,35)
        self.deleteBtn = pg.Rect(257,5,58,35)

        self.readingNow = False
        self.t2 = Thread(target=App.checkTime_loop, args=(self,))
        self.t2.start()
        self.sensor = ""
        self.takeReadFlag = True
        self.calNum = "-1111"
        self.update_reads_per_day()
        self.emailer.sendEmail("" , addressList, 
                               """This is a test email to ensure you will actually receive an email should the sensors detect a reading out of range.""",
                                "Test email for fish sensors")

    def reader(self,sensor):
        if sensor in self.sensorList:
            return str(sensor.getRead())
        else:
            return "NULL"

    def createPHSensor(self):
        try:
            try:
                self.sensorList.remove(self.ph)
            except Exception:
                pass
            self.ph = Sensors("pH", cfg["units"]["PH"], cfg["highRange"]["PH"], cfg["lowRange"]["PH"], "r1_ph_data.csv", 
                         2, 99, addressList, cfg["daysStored"]["days"], cfg["readsPerDay"]["reads"], "PH", "", urlpH, valuespH)
            self.sensorList.append(self.ph)
            self.ph.getRead()
            self.ph.currRead = str(self.ph.getRead())
            if self.ph.currRead is "NULL":
                self.emailer.warning("", addressList, "pH")
                self.sensorList.remove(self.ph)
        except Exception as e:
            t = int(time.time())
            errorstring = time.ctime(t) + ": Error: %s" % str(e)
            try:
                self.sensorList.remove(self.ph)
            except Exception:
                pass
            print(errorstring)

    def createConductivitySensor(self):
        try:
            try:
                self.sensorList.remove(self.conductivity)
            except Exception:
                pass
            self.conductivity = Sensors("Cond", cfg["units"]["EC"], cfg["highRange"]["EC"], cfg["lowRange"]["EC"], "r1_cd_data.csv", 
                         1, 100, addressList, cfg["daysStored"]["days"], cfg["readsPerDay"]["reads"], "EC", cfg["probeType"]["EC"], 
                         urlCond, valuesCond)
            self.sensorList.append(self.conductivity)
            self.conductivity.getRead()
            read2 = self.conductivity.getRead().split(",")[0]
            self.conductivity.currRead = str(read2)
            if self.conductivity.currRead is "NULL":
                self.emailer.warning("", addressList, "Conductivity")
                self.sensorList.remove(self.conductivity)
        except Exception as e:
            t = int(time.time())
            errorstring = time.ctime(t) + ": Error: %s" % str(e)
            try:
                self.sensorList.remove(self.conductivity)
            except Exception:
                pass
            print(errorstring)

    def createdOxygenSensor(self):
        try:
            try:
                self.sensorList.remove(self.dOxygen)
            except Exception:
                pass
            self.dOxygen = Sensors("DO", cfg["units"]["DO"], cfg["highRange"]["DO"], cfg["lowRange"]["DO"], "r1_do_data.csv", 
                             3, 97, addressList, cfg["daysStored"]["days"], cfg["readsPerDay"]["reads"], "DO", "", urlDO, valuesDO)
            self.sensorList.append(self.dOxygen)
            self.dOxygen.getRead()
            self.dOxygen.currRead = str(self.dOxygen.getRead())
            if self.dOxygen.currRead is "NULL":
                self.emailer.warning("", addressList, "Dissolved Oxygen")
                self.sensorList.remove(self.dOxygen)
        except Exception as e:
            try:
                self.sensorList.remove(self.dOxygen)
            except Exception:
                pass
            t = int(time.time())
            errorstring = time.ctime(t) + ": Error: %s" % str(e)
            print(errorstring)

    def createTemperatureSensor(self):
        try:
            self.temperature = Sensors("Temp", cfg["units"]["T"], cfg["highRange"]["T"], cfg["lowRange"]["T"], "r1_tp_data.csv", 
                             0, 102, addressList, cfg["daysStored"]["days"], cfg["readsPerDay"]["reads"], "T", "", urlTemp, valuesTemp)
            self.sensorList.append(self.temperature)
            self.temperature.getRead()
            self.temperature.currRead = str(self.temperature.getRead())
            if self.temperature.currRead is "NULL":
                self.emailer.warning("", addressList, "Temperature")
                self.sensorList.remove(self.temperature)
        except Exception as e:
            try:
                self.sensorList.remove(self.temperature)
            except Exception:
                pass
            t = int(time.time())
            errorstring = time.ctime(t) + ": Error: %s" % str(e)
            print(errorstring)

    # Creates objects of type Sensors that can take reads and write to
    # appropriate files and adds the sensors to a list
    # <--------------------NOTE-------------------->
    # If you don't want a sensor, comment it out here with a '#'
    def createSensors(self):
        self.sensorList = []
        self.createPHSensor()
        self.createConductivitySensor()
        self.createdOxygenSensor()
        self.createTemperatureSensor()
                
        # Limits file size
        for probes in self.sensorList:
            probes.limitFileSize()

    # Attempts to do a command 3 times before failing
    def tryThree(self, command, sensor):
        color = pg.Color("yellow")
        myfont = pg.font.SysFont("monospace", 18)
        failRetry = myfont.render("Calibration Step Failed", 1, color)
        failRetrypos = failRetry.get_rect()
        failRetrypos.centerx = self.background.get_rect().centerx
        failRetrypos.centery = self.background.get_rect().centery
        maxTries = 3
        for i in range(0, maxTries):
            if sensor.calibrateSensor(command) == "Success":
                return True
        self.viewScreen.fill((0,0,0))
        self.viewScreen.blit(failRetry, failRetrypos)
        pg.display.update()
        time.sleep(2)
        self.viewScreen.fill((0,0,0))
        pg.display.update()
        pg.event.clear()        
        return False

    # pH Calibration
    def pH_calibrate(self):
        try:
            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("yellow")
            myfont.set_underline(True)
            titleScreen = myfont.render("Calibrate pH", 1, color)
            myfont.set_underline(False)
            myfont = pg.font.SysFont("monospace", 15)
            step1 = myfont.render("1. Remove cap, rinse probe", 1, color)
            step2 = myfont.render("2. Pour solution in cup", 1, color)
            step3 = myfont.render("3. Sit probe in solution 1-2 min", 1, color)
            step4 = myfont.render("1. Rinse off pH probe", 1, color)
            step5 = myfont.render("4. Press the Calibrate button", 1, color)
            myfont = pg.font.SysFont("monospace", 18)
            singlePt = myfont.render("Single point", 1, color)
            dualPt = myfont.render("Two point", 1, color)
            triPt = myfont.render("Three point", 1, color)
            successfulCal = myfont.render("Calibration Successful", 1, color)
            failCal = myfont.render("Calibration Failed", 1, color)
            failRetry = myfont.render("Try Again", 1, color)
            part1Cal = myfont.render("Calibrate", 1, color)
            pointCal = ""

            titlepos = titleScreen.get_rect()
            titlepos.centerx = self.background.get_rect().centerx
            titlepos.centery = self.background.get_rect().top + 20
            singlePtpos = singlePt.get_rect()
            singlePtpos.centerx = self.middleBtn.centerx
            singlePtpos.centery = self.middleBtn.centery
            dualPtpos = dualPt.get_rect()
            dualPtpos.centerx = self.btmLeft.centerx
            dualPtpos.centery = self.btmLeft.centery
            triPtpos = triPt.get_rect()
            triPtpos.centerx = self.btmRight.centerx
            triPtpos.centery = self.btmRight.centery
            step1pos = step1.get_rect()
            step1pos.centerx = self.topLeft.centerx + 70
            step1pos.centery = self.topLeft.centery - 30
            step2pos = step2.get_rect()
            step2pos.centerx = self.topLeft.centerx + 70
            step2pos.centery = self.topLeft.centery - 10
            step3pos = step3.get_rect()
            step3pos.centerx = self.topLeft.centerx + 70
            step3pos.centery = self.topLeft.centery + 10
            step4pos = step4.get_rect()
            step4pos.centerx = self.topLeft.centerx + 70
            step4pos.centery = self.topLeft.centery - 30
            step5pos = step5.get_rect()
            step5pos.centerx = self.topLeft.centerx + 70
            step5pos.centery = self.topLeft.centery + 30
            successfulCalpos = successfulCal.get_rect()
            successfulCalpos.centerx = self.background.get_rect().centerx
            successfulCalpos.centery = self.background.get_rect().centery
            failCalpos = failCal.get_rect()
            failCalpos.centerx = self.background.get_rect().centerx
            failCalpos.centery = self.background.get_rect().centery
            failurepos = failRetry.get_rect()
            failurepos.centerx = self.btmRight.centerx
            failurepos.centery = self.btmRight.centery
            part1pos = part1Cal.get_rect()
            part1pos.centerx = self.btmRight.centerx
            part1pos.centery = self.btmRight.centery

            midPt = ""
            lowPt = ""
            highPt = ""
            phPtCal = -1
            phStepNum = -1
            self.viewScreen.fill((0,0,0))
            if(self.readingNow == False):
                while(1):
                    pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
                    pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)
                    pg.gfxdraw.rectangle(self.viewScreen, self.btmRight, color)
                    if phPtCal == -1:
                        pg.gfxdraw.rectangle(self.viewScreen, self.btmLeft, color)
                        pg.gfxdraw.rectangle(self.viewScreen, self.middleBtn, color)
                        self.viewScreen.blit(singlePt, singlePtpos)
                        self.viewScreen.blit(dualPt, dualPtpos)
                        self.viewScreen.blit(triPt, triPtpos)
                    else:
                        self.viewScreen.blit(part1Cal, part1pos)
                    self.viewScreen.blit(titleScreen, titlepos)
                    pg.event.clear()
                    pg.display.update()     
                    pg.event.wait()
                    if(self.readingNow == False):
                        for event in pg.event.get():                
                                if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                    self.done = True
                                    return
                                elif event.type == pg.MOUSEBUTTONDOWN:
                                    # Determine the Pt Calibration
                                    if phPtCal == -1:
                                        if self.btmRight.collidepoint(event.pos):
                                            phPtCal = 3
                                            self.viewScreen.fill((0,0,0))
                                        elif self.btmLeft.collidepoint(event.pos):
                                            phPtCal = 2
                                            self.viewScreen.fill((0,0,0))
                                        elif self.middleBtn.collidepoint(event.pos):
                                            phPtCal = 1
                                            self.viewScreen.fill((0,0,0))
                                    elif self.btmRight.collidepoint(event.pos):
                                        if self.ph.i2cAddress != -1:
                                            if phStepNum == -1:
                                                    self.numpad_event("Enter MidPt","",1)
                                                    midPt = self.calNum
                                                    self.calNum = "-1111"
                                                    phStepNum = 1
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(part1Cal, part1pos)
                                                    self.viewScreen.blit(step1, step1pos)
                                                    self.viewScreen.blit(step2, step2pos)
                                                    self.viewScreen.blit(step3, step3pos)
                                                    self.viewScreen.blit(step5, step5pos)
                                                    pg.display.update()
                                            elif phStepNum == 1:
                                                if self.tryThree('CAL,mid,' + str(midPt), self.ph):
                                                    phStepNum = 2
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(successfulCal, successfulCalpos)
                                                    pg.display.update()
                                                    time.sleep(1)
                                                    if phPtCal == 1:
                                                        self.calNum = "-1111"
                                                        return
                                            elif phStepNum == 2:
                                                    self.numpad_event("Enter LowPt","",1)
                                                    lowPt = self.calNum
                                                    self.calNum = "-1111"
                                                    phStepNum = 3
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(part1Cal, part1pos)
                                                    self.viewScreen.blit(step4, step4pos)
                                                    self.viewScreen.blit(step2, step2pos)
                                                    self.viewScreen.blit(step3, step3pos)
                                                    self.viewScreen.blit(step5, step5pos)
                                            elif phStepNum == 3:
                                                if self.tryThree('CAL,low,' + lowPt, self.ph):
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(successfulCal, successfulCalpos)
                                                    pg.display.update()
                                                    time.sleep(1)
                                                    phStepNum = 4
                                                    if phPtCal == 2:
                                                        self.calNum = "-1111"
                                                        return
                                            elif phStepNum == 4:
                                                    self.numpad_event("Enter HighPt","",1)
                                                    highPt = self.calNum
                                                    self.calNum = "-1111"
                                                    phStepNum = 5
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(part1Cal, part1pos)
                                                    self.viewScreen.blit(step4, step4pos)
                                                    self.viewScreen.blit(step2, step2pos)
                                                    self.viewScreen.blit(step3, step3pos)
                                                    self.viewScreen.blit(step5, step5pos)
                                            elif phStepNum == 5:
                                                if self.tryThree('CAL,high,' + highPt, self.ph):
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(successfulCal, successfulCalpos)
                                                    pg.display.update()
                                                    time.sleep(1)
                                                    self.calNum = "-1111"
                                                    return
                                    elif self.backBtn.collidepoint(event.pos):
                                        self.calNum = "-1111"
                                        return
        except:
            self.viewScreen.fill((0,0,0))
            self.viewScreen.blit(failCal, failCalpos)
            pg.display.update()
            time.sleep(1)
            self.calNum = "-1111"
            return

    # Conductivity Calibration - currently only has single point calibration, 2-pt cal exists and may be added in the future
    def cond_calibrate(self):
        try:
            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("yellow")
            myfont.set_underline(True)
            titleScreen = myfont.render("Calibrate Conductivity", 1, color)
            myfont.set_underline(False)
            myfont = pg.font.SysFont("monospace", 18)
            calibText = myfont.render("Calibrate", 1, color)
            myfont = pg.font.SysFont("monospace", 15)
            step1 = myfont.render("1. Pour solution in cup", 1, color)
            step2 = myfont.render("2. Shake probe", 1, color)
            step3 = myfont.render("3. Sit probe in solution", 1, color)
            step4 = myfont.render("1. Starts with dry calibration", 1, color)
            step5 = myfont.render("4. Press Calibrate", 1, color)
            step6 = myfont.render("This will take some time...", 1, color)
            successfulCal = myfont.render("Calibration Successful", 1, color)
            failCal = myfont.render("Calibration Failed", 1, color)
            failRetry = myfont.render("Try Again", 1, color)
            pointCal = ""

            titlepos = titleScreen.get_rect()
            titlepos.centerx = self.background.get_rect().centerx + 20
            titlepos.centery = self.background.get_rect().top + 20
            calibTextpos = calibText.get_rect()
            calibTextpos.centerx = self.btmRight.centerx
            calibTextpos.centery = self.btmRight.centery
            step1pos = step1.get_rect()
            step1pos.centerx = self.topLeft.centerx + 60
            step1pos.centery = self.topLeft.centery - 30
            step4pos = step4.get_rect()
            step4pos.centerx = self.topLeft.centerx + 60
            step4pos.centery = self.topLeft.centery - 30
            step2pos = step2.get_rect()
            step2pos.centerx = self.topLeft.centerx + 60
            step2pos.centery = self.topLeft.centery - 10
            step3pos = step3.get_rect()
            step3pos.centerx = self.topLeft.centerx + 60
            step3pos.centery = self.topLeft.centery + 10
            step6pos = step6.get_rect()
            step6pos.centerx = self.background.get_rect().centerx
            step6pos.centery = self.background.get_rect().centery
            successfulCalpos = successfulCal.get_rect()
            successfulCalpos.centerx = self.background.get_rect().centerx
            successfulCalpos.centery = self.background.get_rect().centery
            failCalpos = failCal.get_rect()
            failCalpos.centerx = self.background.get_rect().centerx
            failCalpos.centery = self.background.get_rect().centery
            failurepos = failRetry.get_rect()
            failurepos.centerx = self.btmRight.centerx
            failurepos.centery = self.btmRight.centery

            condCal = ""
            stepNum = 0
            self.viewScreen.fill((0,0,0))
            if(self.readingNow == False):
                while(1):
                    pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
                    pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)
                    pg.gfxdraw.rectangle(self.viewScreen, self.btmRight, color)
                    self.viewScreen.blit(titleScreen, titlepos)
                    self.viewScreen.blit(calibText, calibTextpos)
                    pg.event.clear()
                    pg.display.update()     
                    pg.event.wait()
                    if(self.readingNow == False):
                        for event in pg.event.get():
                                if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                    self.done = True
                                    return
                                elif event.type == pg.MOUSEBUTTONDOWN:
                                    if self.btmRight.collidepoint(event.pos):
                                        if self.conductivity.i2cAddress != -1:
                                            if stepNum == 0:
                                                        self.numpad_event("Cal Value","",1)
                                                        self.viewScreen.fill((0,0,0))
                                                        if self.tryThree('CAL,clear', self.conductivity):
                                                            stepNum = 1
                                                            condCal = str(self.calNum)
                                                            self.viewScreen.fill((0,0,0))
                                                            self.viewScreen.blit(step4, step4pos)
                                            elif stepNum == 1:
                                                if self.tryThree('CAL,dry', self.conductivity):
                                                    stepNum = 2
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(successfulCal, successfulCalpos)
                                                    pg.display.update()
                                                    time.sleep(1)
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(step2, step2pos)
                                                    self.viewScreen.blit(step3, step3pos)
                                                    self.viewScreen.blit(step1, step1pos)
                                                    pg.display.update()                 
                                            elif stepNum == 2:
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(step6, step6pos)
                                                    pg.display.update()
                                                    highCal = int(self.calNum) * 1.4
                                                    lowCal = int(self.calNum) * .6
                                                    hCal = 0.0
                                                    lCal = 0.0
                                                    lCal = float(lowCal)
                                                    hCal = float(highCal)
                                                    tempRead = 0.0
                                                    # Takes reads until 2 consecutive
                                                    # reads within the 40% variance are
                                                    # less than 10 apart
                                                    for i in range(0,15):
                                                        if(stepNum != 3):
                                                            calRead = self.conductivity.getRead()
                                                            if tempRead < hCal and tempRead > lCal:
                                                                if((float(calRead) - tempRead) < 10):
                                                                    stepNum = 3 
                                                            tempRead = float(calRead)
                                                    self.viewScreen.fill((0,0,0))
                                            if stepNum == 3:
                                                if self.tryThree('CAL,' + condCal, self.conductivity):
                                                    stepNum = 4
                                                    self.viewScreen.fill((0,0,0))
                                                    self.viewScreen.blit(successfulCal, successfulCalpos)
                                                    pg.display.update()
                                                    time.sleep(1)
                                                    self.calNum = "-1111"
                                                    return
                                    elif self.backBtn.collidepoint(event.pos):
                                        self.calNum = "-1111"
                                        return
        except:
            self.viewScreen.fill((0,0,0))
            self.viewScreen.blit(failCal, failCalpos)
            pg.display.update()
            time.sleep(1)
            self.calNum = "-1111"
            return

    # Temperature Calibration
    def temp_calibrate(self):
        try:
            self.viewScreen.fill((0,0,0))
            pg.display.update()
            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("yellow")
            myfont.set_underline(True)
            titleScreen = myfont.render("Calibrate Temperature", 1, color)
            myfont.set_underline(False)
            myfont = pg.font.SysFont("monospace", 18)
            calibText = myfont.render("Calibrate", 1, color)
            myfont = pg.font.SysFont("monospace", 15)
            step1 = myfont.render("1. Put probe in solution", 1, color)
            step2 = myfont.render("2. Enter solution temperature", 1, color)
            step3 = myfont.render("3. Press calibrate", 1, color)
            successfulCal = myfont.render("Calibration Successful", 1, color)
            failCal = myfont.render("Calibration Failed", 1, color)
            failRetry = myfont.render("Try Again", 1, color)

            titlepos = titleScreen.get_rect()
            titlepos.centerx = self.background.get_rect().centerx + 20
            titlepos.centery = self.background.get_rect().top + 20
            calibTextpos = calibText.get_rect()
            calibTextpos.centerx = self.btmRight.centerx
            calibTextpos.centery = self.btmRight.centery
            step1pos = step1.get_rect()
            step1pos.centerx = self.topLeft.centerx + 60
            step1pos.centery = self.topLeft.centery - 30
            step2pos = step2.get_rect()
            step2pos.centerx = self.topLeft.centerx + 60
            step2pos.centery = self.topLeft.centery - 10
            step3pos = step3.get_rect()
            step3pos.centerx = self.topLeft.centerx + 60
            step3pos.centery = self.topLeft.centery + 10
            successfulCalpos = successfulCal.get_rect()
            successfulCalpos.centerx = self.background.get_rect().centerx
            successfulCalpos.centery = self.background.get_rect().centery
            failCalpos = failCal.get_rect()
            failCalpos.centerx = self.background.get_rect().centerx
            failCalpos.centery = self.background.get_rect().centery
            if(self.readingNow == False):
                stepNum = 0
                while(1):
                    self.viewScreen.fill((0,0,0))
                    pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
                    pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)
                    pg.gfxdraw.rectangle(self.viewScreen, self.btmRight, color)
                    self.viewScreen.blit(titleScreen, titlepos)
                    self.viewScreen.blit(calibText, calibTextpos)
                    if self.calNum != "-1111":
                        self.viewScreen.blit(step1, step1pos)
                        self.viewScreen.blit(step2, step2pos)
                        self.viewScreen.blit(step3, step3pos)                                       
                    pg.event.clear()
                    pg.display.update()     
                    pg.event.wait()
                    if(self.readingNow == False):
                        for event in pg.event.get():
                                if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                    self.done = True
                                    return
                                elif event.type == pg.MOUSEBUTTONDOWN:
                                    if self.btmRight.collidepoint(event.pos):
                                        if self.temperature.i2cAddress != -1:
                                            if stepNum == 0:
                                                if self.calNum == "-1111":
                                                    self.numpad_event("Cal Value","",1)
                                                    self.viewScreen.fill((0,0,0))
                                                    stepNum = 1
                                            elif stepNum == 1:
                                                if self.tryThree('CAL,clear', self.temperature):
                                                    if self.tryThree('CAL,' + str(self.calNum), self.temperature):
                                                        self.viewScreen.fill((0,0,0))
                                                        self.viewScreen.blit(successfulCal, successfulCalpos)
                                                        pg.display.update()
                                                        time.sleep(1)
                                                        self.calNum = "-1111"
                                                        return
                                    elif self.backBtn.collidepoint(event.pos):
                                        self.calNum = "-1111"
                                        return
        except:
            self.viewScreen.fill((0,0,0))
            self.viewScreen.blit(failCal, failCalpos)
            pg.display.update()
            time.sleep(1)
            self.calNum = "-1111"
            return

    # Dissolved Oxygen Calibration
    def dOxygen_calibrate(self):
            try:
                myfont = pg.font.SysFont("monospace", 20)
                color = pg.Color("yellow")
                myfont.set_underline(True)
                titleScreen = myfont.render("Calibrate dOxygen", 1, color)
                myfont.set_underline(False)
                myfont = pg.font.SysFont("monospace", 18)
                calibText = myfont.render("Calibrate", 1, color)
                myfont = pg.font.SysFont("monospace", 15)
                step1 = myfont.render("1. Remove cap", 1, color)
                step2 = myfont.render("2. Let probe sit 30 seconds", 1, color)
                step3 = myfont.render("3. Press calibrate", 1, color)
                step4 = myfont.render("1. Stir probe in solution", 1, color)
                step5 = myfont.render("2. Sit probe in solution 90 sec", 1, color)
                step6 = myfont.render("3. Press calibrate", 1, color)
                singlePt = myfont.render("Single-pt", 1, color)
                dualPt = myfont.render("Dual-pt", 1, color)
                successfulCal = myfont.render("Calibration Successful", 1, color)
                failCal = myfont.render("Calibration Failed", 1, color)
                failRetry = myfont.render("Try Again", 1, color)
                part1Cal = myfont.render("Calibrate", 1, color)
                pointCal = ""

                titlepos = titleScreen.get_rect()
                titlepos.centerx = self.background.get_rect().centerx
                titlepos.centery = self.background.get_rect().top + 20
                singlePtpos = singlePt.get_rect()
                singlePtpos.centerx = self.btmLeft.centerx
                singlePtpos.centery = self.btmLeft.centery
                dualPtpos = dualPt.get_rect()
                dualPtpos.centerx = self.btmRight.centerx
                dualPtpos.centery = self.btmRight.centery
                step1pos = step1.get_rect()
                step1pos.centerx = self.topLeft.centerx + 60
                step1pos.centery = self.topLeft.centery - 30
                step2pos = step2.get_rect()
                step2pos.centerx = self.topLeft.centerx + 60
                step2pos.centery = self.topLeft.centery - 10
                step3pos = step3.get_rect()
                step3pos.centerx = self.topLeft.centerx + 60
                step3pos.centery = self.topLeft.centery + 10
                step4pos = step4.get_rect()
                step4pos.centerx = self.topLeft.centerx + 60
                step4pos.centery = self.topLeft.centery - 30
                step5pos = step5.get_rect()
                step5pos.centerx = self.topLeft.centerx + 60
                step5pos.centery = self.topLeft.centery - 10
                step6pos = step6.get_rect()
                step6pos.centerx = self.topLeft.centerx + 60
                step6pos.centery = self.topLeft.centery + 10
                successfulCalpos = successfulCal.get_rect()
                successfulCalpos.centerx = self.background.get_rect().centerx
                successfulCalpos.centery = self.background.get_rect().centery
                failurepos = failRetry.get_rect()
                failurepos.centerx = self.btmRight.centerx
                failurepos.centery = self.btmRight.centery
                failCalpos = failCal.get_rect()
                failCalpos.centerx = self.background.get_rect().centerx
                failCalpos.centery = self.background.get_rect().centery
                part1pos = part1Cal.get_rect()
                part1pos.centerx = self.btmRight.centerx
                part1pos.centery = self.btmRight.centery

                ptCals = -1
                stepNum = 0
                self.viewScreen.fill((0,0,0))
                while(1):                
                    if(self.readingNow == False):
                        if self.calNum != "1":
                                self.viewScreen.blit(singlePt, singlePtpos)
                                self.viewScreen.blit(dualPt, dualPtpos)
                        pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
                        pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)
                        pg.gfxdraw.rectangle(self.viewScreen, self.btmRight, color)
                        if ptCals == -1:
                                pg.gfxdraw.rectangle(self.viewScreen, self.btmLeft, color)
                        self.viewScreen.blit(titleScreen, titlepos)
                                       
                        pg.event.clear()
                        pg.display.update()     
                        pg.event.wait()
                        if(self.readingNow == False):
                            for event in pg.event.get():
                                        if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                            self.done = True
                                            return
                                        elif event.type == pg.MOUSEBUTTONDOWN:
                                            # Dual Point Calibration
                                            if self.btmRight.collidepoint(event.pos):
                                                if self.dOxygen.i2cAddress != -1:
                                                    if stepNum == 0:
                                                        if self.tryThree('CAL,clear', self.dOxygen):
                                                            ptCals = 1
                                                            stepNum = 1
                                                            self.calNum = "1"
                                                            self.viewScreen.fill((0,0,0))
                                                            self.viewScreen.blit(part1Cal, part1pos)
                                                            self.viewScreen.blit(step1, step1pos)
                                                            self.viewScreen.blit(step2, step2pos)
                                                            self.viewScreen.blit(step3, step3pos)
                                                    elif stepNum == 1:
                                                        if self.tryThree('CAL', self.dOxygen):
                                                            stepNum = 2
                                                            self.viewScreen.fill((0,0,0))
                                                            self.viewScreen.blit(successfulCal, successfulCalpos)
                                                            pg.display.update()
                                                            time.sleep(1)
                                                            self.viewScreen.fill((0,0,0))
                                                            self.viewScreen.blit(part1Cal, part1pos)
                                                            self.viewScreen.blit(step4, step4pos)
                                                            self.viewScreen.blit(step5, step5pos)
                                                            self.viewScreen.blit(step6, step6pos)
                                                    elif stepNum == 2:
                                                        if self.tryThree('CAL,0', self.dOxygen):
                                                                self.viewScreen.fill((0,0,0))
                                                                self.viewScreen.blit(successfulCal, successfulCalpos)
                                                                pg.display.update()
                                                                time.sleep(1)
                                                                self.calNum = "-1111"
                                                                return
                                            # Single Point Calibration
                                            elif self.btmLeft.collidepoint(event.pos):
                                                    if stepNum == 0:
                                                        if self.tryThree('CAL,clear', self.dOxygen):
                                                            ptCals = 1
                                                            stepNum = 2
                                                            self.calNum = "1"
                                                            self.viewScreen.fill((0,0,0))
                                                            self.viewScreen.blit(part1Cal, part1pos)
                                                            self.viewScreen.blit(step1, step1pos)
                                                            self.viewScreen.blit(step2, step2pos)
                                                            self.viewScreen.blit(step3, step3pos)
                                                            pg.display.update()
                                            elif self.backBtn.collidepoint(event.pos):
                                                self.calNum = "-1111"
                                                return
            except:
                self.viewScreen.fill((0,0,0))
                self.viewScreen.blit(failCal, failCalpos)
                pg.display.update()
                time.sleep(1)
                self.calNum = "-1111"
                return

    def getLowRange(self, sensor, sensorTag):
        if sensor in self.sensorList:
            return sensor.lowRange
        else:
            return cfg["lowRange"][sensorTag]

    def getHighRange(self, sensor, sensorTag):
        if sensor in self.sensorList:
            return sensor.highRange
        else:
            return cfg["highRange"][sensorTag]

    # Screen shows "Taking Reads..."
    def taking_reads_loop(self):
        color = pg.Color("steelblue1")
        myfont = pg.font.SysFont("monospace", 15)  
        takeReadsText0 = myfont.render("Taking Reads   ", 1, color)                             
        takeReadsText1 = myfont.render("Taking Reads.  ", 1, color)
        takeReadsText2 = myfont.render("Taking Reads.. ", 1, color)
        takeReadsText3 = myfont.render("Taking Reads...", 1, color)
        takeReadsTextpos = takeReadsText3.get_rect()
        takeReadsTextpos.centerx = self.background.get_rect().centerx
        takeReadsTextpos.centery = self.background.get_rect().centery
        while(self.readingNow):
            self.viewScreen.blit(takeReadsText0, takeReadsTextpos)
            self.viewScreen.blit(takeReadsText0, takeReadsTextpos)
            self.viewScreen.blit(takeReadsText0, takeReadsTextpos)
            pg.display.update()
            if(self.readingNow):
                time.sleep(2)
                self.viewScreen.blit(takeReadsText1, takeReadsTextpos)
                pg.display.update()
                if(self.readingNow):    
                    time.sleep(2)                  
                    self.viewScreen.blit(takeReadsText2, takeReadsTextpos)
                    pg.display.update()
                    if(self.readingNow):
                        time.sleep(2)
                        self.viewScreen.blit(takeReadsText3, takeReadsTextpos)
                        pg.display.update()
                        if(self.readingNow):
                            time.sleep(2)
            self.viewScreen.fill((0,0,0))
        self.viewScreen.fill((0,0,0))

    # A constantly running loop that has an individual thread
    # Checks the time for taking automated reads
    def checkTime_loop(self):
        while(self.done != True):
            try:
                currMin = datetime.now().minute
                currHour = datetime.now().hour
                if int(currHour) < 1:
                    currHour = "0"
                else:
                    currHour = str(round(int(currHour), 0))
                if currMin > 9:
                    uCurrTime = currHour + "." + str(round(currMin, 0))
                elif currMin < 1:
                    uCurrTime = currHour + ".0"
                else:
                    uCurrTime = currHour + ".0" + str(round(currMin, 0))
                currTime = str(uCurrTime)
                #potential increase to speed, try:
                #self.timeList.index(currTime)
                if(currTime in self.timeList and self.takeReadFlag is True) or currTime == "0.0":           
                    self.takeReadFlag = False
                    self.waitTime = currMin + 1
                    if(self.waitTime > 59):
                        self.waitTime = 0
                    self.readingNow = True
                    try:
                        takingReads = Thread(target=App.taking_reads_loop, args=(self,))
                        takingReads.start()
                    except:
                        continue
                    for prob in self.sensorList:
                        if(prob.i2cAddress != -1):
                            reads = prob.takeRead()
                            reads = reads[:-1]
                            [float(i) for i in reads]
                            if(len(reads) > 0):
                                avgRead = sum(reads) / len(reads)
                                avgRead2 = round(avgRead,1)
                                prob.currRead = str(avgRead2)
                    pg.event.clear()
                    self.readingNow = False
                elif self.waitTime < int(currMin) and self.waitTime != 0:
                    self.takeReadFlag = True
            except Exception as e:
                pass
            try:
                if cfg["needUpdate"]["update"] == "yes":
                    self.createSensors()
                    cfg["needUpdate"]["update"] = "no"
                    with open("/home/pi/FishCode/Configure.yaml", "w") as f:
                        yaml.dump(cfg, f)
                    addressList = []
                    emailFile = open("/home/pi/FishCode/EmailList.txt", "r")
                    with open("/home/pi/FishCode/EmailList.txt", "r") as f:
                        for line in f:
                            cleanLine = line.strip()
                            if cleanLine:
                               addressList.append(cleanLine)
                    emailFile.close()
                    for probe in self.sensorList:
                        probe.recipients = addressList
                    self.update_reads_per_day()
            except Exception as e:
                pass
                time.sleep(50)

    # Updates the list of times checked in the CheckTime() function
    def update_reads_per_day(self):
        self.timeList = []
        hours = 24 / int(self.readsPerDay)
        i = 0.00
        j = 0.00
        while i < 24:
            i = hours + i
            if i < 24:
                addHour = int(i)
                y = i % 1
                j = (y * 60) / 100
                addTime = addHour + round(j, 2)
                addThis = str(round(addTime, 2))
                self.timeList.append(addThis)

    # Update range values screen
    def update_event_screen(self, sensorName, sensorTag, sensor):
            self.viewScreen.fill((0,0,0))
            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("orange")
            myfont.set_underline(True)
            title = myfont.render(sensorName + " Range", 1, color)
            myfont.set_underline(False)
            pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)

            currRead = myfont.render(sensor.currRead, 1, color)
            lowTitle = myfont.render("Low", 1, color)
            highTitle = myfont.render("High", 1, color)
            lowRange = myfont.render(str(self.getLowRange(sensor, sensorTag)), 1, color)
            highRange = myfont.render(str(self.getHighRange(sensor, sensorTag)), 1, color)
            calibrate = myfont.render("Calibrate", 1, color)
            refresh = myfont.render("Refresh", 1, color)

            textpos = title.get_rect()
            textpos.centerx = self.background.get_rect().centerx
            textpos.centery = self.background.get_rect().top + 20
            self.viewScreen.blit(title, textpos)
            pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.topLeft, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.btmLeftSmall, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.btmRightSmall, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.middleBtnSmall, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.topRight, color)

            textpos = calibrate.get_rect()
            textpos.centerx = self.topLeft.centerx
            textpos.centery = self.topLeft.centery
            self.viewScreen.blit(calibrate, textpos)
            textpos = refresh.get_rect()
            textpos.centerx = self.topRight.centerx
            textpos.centery = self.topRight.centery
            self.viewScreen.blit(refresh, textpos)
            textpos = currRead.get_rect()
            textpos.centerx = self.middleBtnSmall.centerx
            textpos.centery = self.middleBtnSmall.centery
            self.viewScreen.blit(currRead, textpos)
            textpos = lowTitle.get_rect()
            textpos.centerx = self.btmLeftSmall.centerx
            textpos.centery = self.btmLeftSmall.centery - 10
            self.viewScreen.blit(lowTitle, textpos)
            textpos = highTitle.get_rect()
            textpos.centerx = self.btmRightSmall.centerx
            textpos.centery = self.btmRightSmall.centery - 10
            self.viewScreen.blit(highTitle, textpos)
            textpos = highRange.get_rect()
            textpos.centerx = self.btmRightSmall.centerx
            textpos.centery = self.btmRightSmall.centery + 10
            self.viewScreen.blit(highRange, textpos)
            textpos = lowRange.get_rect()
            textpos.centerx = self.btmLeftSmall.centerx
            textpos.centery = self.btmLeftSmall.centery + 10
            self.viewScreen.blit(lowRange, textpos)
            pg.display.update()     

    # Numpad screen
    def numpad_event_screen(self, lowUp, ulrange, cal):
            self.viewScreen.fill((0,0,0))
            self.calNum = -1111
            myfont = pg.font.SysFont("monospace", 60)
            color = pg.Color("yellow")
            oneNum = myfont.render("1", 1, color)
            twoNum = myfont.render("2", 1, color)
            threeNum = myfont.render("3", 1, color)
            fourNum = myfont.render("4", 1, color)
            fiveNum = myfont.render("5", 1, color)
            sixNum = myfont.render("6", 1, color)
            sevenNum = myfont.render("7", 1, color)
            eightNum = myfont.render("8", 1, color)                        
            nineNum = myfont.render("9", 1, color)
            zeroNum = myfont.render("0", 1, color)
            periodNum = myfont.render(".", 1, color)
            myfont = pg.font.SysFont("monospace", 20)
            myfont.set_underline(True)

            if cal is 0:
                title = myfont.render("Enter New Range", 1, color)
                newRangeText = myfont.render("New " + lowUp + " Range:", 1, color)
                pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
                pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)
            elif cal is 1:
                title = myfont.render("Enter Calibration", 1, color)
                newRangeText = myfont.render(lowUp + ":", 1, color)
            elif cal is 3:
                title = myfont.render("Enter Reads/Day", 1, color)
                newRangeText = myfont.render("Reads/Day:", 1, color)
                pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
                pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)
            elif cal is 4:
                title = myfont.render("Enter Days Kept", 1, color)
                newRangeText = myfont.render("Days Kept:", 1, color)
                pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
                pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)

            myfont = pg.font.SysFont("monospace", 15)
            submit = myfont.render("Submit", 1, color)

            pg.draw.polygon(self.viewScreen, color, ((305,21),(265,21),(275,27),(265,21),(275,14),(265,21)), 2)

            pg.gfxdraw.rectangle(self.viewScreen, self.one, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.two, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.three, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.four, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.five, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.six, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.seven, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.eight, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.nine, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.period, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.zero, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.submitBtn, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.deleteBtn, color)

            textpos = oneNum.get_rect()
            textpos.centerx = self.one.centerx
            textpos.centery = self.one.centery
            self.viewScreen.blit(oneNum, textpos)
            textpos = twoNum.get_rect()
            textpos.centerx = self.two.centerx
            textpos.centery = self.two.centery
            self.viewScreen.blit(twoNum, textpos)
            textpos = threeNum.get_rect()
            textpos.centerx = self.three.centerx
            textpos.centery = self.three.centery
            self.viewScreen.blit(threeNum, textpos)
            textpos = fourNum.get_rect()
            textpos.centerx = self.four.centerx
            textpos.centery = self.four.centery
            self.viewScreen.blit(fourNum, textpos)
            textpos = fiveNum.get_rect()
            textpos.centerx = self.five.centerx
            textpos.centery = self.five.centery
            self.viewScreen.blit(fiveNum, textpos)
            textpos = sixNum.get_rect()
            textpos.centerx = self.six.centerx
            textpos.centery = self.six.centery
            self.viewScreen.blit(sixNum, textpos)
            textpos = sevenNum.get_rect()
            textpos.centerx = self.seven.centerx
            textpos.centery = self.seven.centery
            self.viewScreen.blit(sevenNum, textpos)
            textpos = eightNum.get_rect()
            textpos.centerx = self.eight.centerx
            textpos.centery = self.eight.centery
            self.viewScreen.blit(eightNum, textpos)
            textpos = nineNum.get_rect()
            textpos.centerx = self.nine.centerx
            textpos.centery = self.nine.centery
            self.viewScreen.blit(nineNum, textpos)
            textpos = periodNum.get_rect()
            textpos.centerx = self.period.centerx
            textpos.centery = self.period.centery - 10
            self.viewScreen.blit(periodNum, textpos)
            textpos = zeroNum.get_rect()
            textpos.centerx = self.zero.centerx
            textpos.centery = self.zero.centery
            self.viewScreen.blit(zeroNum, textpos)
            textpos = submit.get_rect()
            textpos.centerx = self.submitBtn.centerx
            textpos.centery = self.submitBtn.centery
            self.viewScreen.blit(submit, textpos)
            self.viewScreen.blit(newRangeText, (5,195))
            self.viewScreen.blit(title, (50,10))

    # The main menu screen
    def main_menu_screen(self):
            self.viewScreen.fill((0,0,0))
            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("green")
            pHRead = myfont.render(self.ph.currRead, 1, color)
            condRead = myfont.render(self.conductivity.currRead, 1, color)
            dORead = myfont.render(self.dOxygen.currRead, 1, color)
            tempRead = myfont.render(self.temperature.currRead, 1, color)
            myfont.set_underline(True)
            titleScreen = myfont.render("Current Reads", 1, color)
            myfont.set_underline(False)
            titlepH = myfont.render("pH:", 1, color)#TODO try to do a newline character with info, reduces code length
            titleCond = myfont.render("Cond:", 1, color)
            titleDO = myfont.render("DO:", 1, color)
            titleTemp = myfont.render("Temp:", 1, color)
            tLeft = pg.gfxdraw.rectangle(self.viewScreen, self.topLeft, color)
            bLeft = pg.gfxdraw.rectangle(self.viewScreen, self.btmLeft, color)
            tRight = pg.gfxdraw.rectangle(self.viewScreen, self.topRight, color)
            bRight = pg.gfxdraw.rectangle(self.viewScreen, self.btmRight, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.settingsBtn, color)
            pg.draw.circle(self.viewScreen, color, (297,22), 17, 10)
            textpos = titleCond.get_rect()
            textpos.centerx = self.topLeft.centerx 
            textpos.centery = self.topLeft.centery - 10
            self.viewScreen.blit(titleCond, textpos)
            textpos = titlepH.get_rect()
            textpos.centerx = self.btmLeft.centerx
            textpos.centery = self.btmLeft.centery - 10
            self.viewScreen.blit(titlepH, textpos)
            textpos = titleDO.get_rect()
            textpos.centerx = self.topRight.centerx
            textpos.centery = self.topRight.centery - 10
            self.viewScreen.blit(titleDO, textpos)
            textpos = titleTemp.get_rect()
            textpos.centerx = self.btmRight.centerx
            textpos.centery = self.btmRight.centery - 10
            self.viewScreen.blit(titleTemp, textpos)
            textpos = condRead.get_rect()
            textpos.centerx = self.topLeft.centerx
            textpos.centery = self.topLeft.centery + 10
            self.viewScreen.blit(condRead, textpos)
            textpos = dORead.get_rect()
            textpos.centerx = self.topRight.centerx
            textpos.centery = self.topRight.centery + 10
            self.viewScreen.blit(dORead, textpos)
            textpos = pHRead.get_rect()
            textpos.centerx = self.btmLeft.centerx
            textpos.centery = self.btmLeft.centery + 10
            self.viewScreen.blit(pHRead, textpos)
            textpos = tempRead.get_rect()
            textpos.centerx = self.btmRight.centerx
            textpos.centery = self.btmRight.centery + 10
            self.viewScreen.blit(tempRead, textpos)
            textpos = titleScreen.get_rect()
            textpos.centerx = self.background.get_rect().centerx
            textpos.centery = self.background.get_rect().top + 20
            self.viewScreen.blit(titleScreen, textpos)

    # Settings screen
    def settings_event_screen(self):
            self.viewScreen.fill((0,0,0))

            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("yellow")
            titleip = myfont.render("ip Address:", 1, color)#TODO try to do a newline character with info, reduces code length
            titleRefresh = myfont.render("Refresh", 1, color)
            titleSensor = myfont.render("Sensors", 1, color)
            titleDays = myfont.render("Days Kept:", 1, color)
            titleReadsDay = myfont.render("Reads/Day:", 1, color)
            ipEth0 = myfont.render(str(self.eth0), 1, color)
            ipwlan0 = myfont.render(str(self.wlan0), 1, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.settingsBtn, color)
            pg.draw.circle(self.viewScreen, color, (297,22), 17, 10)
            try:
                daysKept = myfont.render(str(self.daysToKeep), 1, color)
            except Exception as e:
                daysKept = myfont.render("Unknown", 1, color)
            try:
                readsPerDay = myfont.render(str(self.readsPerDay), 1, color)
            except Exception as e:
                readsPerDay = myfont.render("Unknown", 1, color)
            tLeft = pg.gfxdraw.rectangle(self.viewScreen, self.topLeft, color)
            bLeft = pg.gfxdraw.rectangle(self.viewScreen, self.btmLeft, color)
            tRight = pg.gfxdraw.rectangle(self.viewScreen, self.topRight, color)
            bRight = pg.gfxdraw.rectangle(self.viewScreen, self.btmRight, color)
            pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
            pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)

            textpos = titleip.get_rect()
            textpos.centerx = self.topLeft.centerx 
            textpos.centery = self.topLeft.centery - 30
            self.viewScreen.blit(titleip, textpos)
            textpos = titleDays.get_rect()
            textpos.centerx = self.btmLeft.centerx
            textpos.centery = self.btmLeft.centery - 10
            self.viewScreen.blit(titleDays, textpos)
            textpos = titleRefresh.get_rect()
            textpos.centerx = self.topRight.centerx
            textpos.centery = self.topRight.centery - 10
            self.viewScreen.blit(titleRefresh, textpos)
            textpos = titleReadsDay.get_rect()
            textpos.centerx = self.btmRight.centerx
            textpos.centery = self.btmRight.centery - 10
            self.viewScreen.blit(titleReadsDay, textpos)
            textpos = ipEth0.get_rect()
            textpos.centerx = self.topLeft.centerx 
            textpos.centery = self.topLeft.centery
            self.viewScreen.blit(ipEth0, textpos)
            textpos = ipwlan0.get_rect()
            textpos.centerx = self.topLeft.centerx 
            textpos.centery = self.topLeft.centery + 30
            self.viewScreen.blit(ipwlan0, textpos)
            textpos = daysKept.get_rect()
            textpos.centerx = self.btmLeft.centerx
            textpos.centery = self.btmLeft.centery + 10
            self.viewScreen.blit(daysKept, textpos)
            textpos = titleSensor.get_rect()
            textpos.centerx = self.topRight.centerx
            textpos.centery = self.topRight.centery + 10
            self.viewScreen.blit(titleSensor, textpos)
            textpos = readsPerDay.get_rect()
            textpos.centerx = self.btmRight.centerx
            textpos.centery = self.btmRight.centery + 10
            self.viewScreen.blit(readsPerDay, textpos)

    # Advanced Settings screen
    def advanced_settings_event_screen(self):
            self.viewScreen.fill((0,0,0))

            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("plum1")
            titleExit = myfont.render("EXIT", 1, color)
            titleEmailLogs = myfont.render("Email Data", 1, color)
            mLeft = pg.gfxdraw.rectangle(self.viewScreen, self.midLeft, color)
            mRight = pg.gfxdraw.rectangle(self.viewScreen, self.midRight, color)

            myfont.set_underline(True)
            titleScreen = myfont.render("Advanced Settings", 1, color)
            myfont.set_underline(False)

            pg.gfxdraw.rectangle(self.viewScreen, self.backBtn, color)
            pg.draw.polygon(self.viewScreen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)

            textpos = titleExit.get_rect()
            textpos.centerx = self.midRight.centerx
            textpos.centery = self.midRight.centery
            self.viewScreen.blit(titleExit, textpos)
            textpos = titleEmailLogs.get_rect()
            textpos.centerx = self.midLeft.centerx 
            textpos.centery = self.midLeft.centery
            self.viewScreen.blit(titleEmailLogs, textpos)
            textpos = titleScreen.get_rect()
            textpos.centerx = self.background.get_rect().centerx
            textpos.centery = self.background.get_rect().top + 20
            self.viewScreen.blit(titleScreen, textpos)

    # Advanced Settings
    def advanced_settings_event(self):
        while(1):
            if(self.readingNow == False):
                self.advanced_settings_event_screen()
                pg.display.update()
                pg.event.clear()
                pg.event.wait()
                if(self.readingNow == False):
                    for event in pg.event.get():
                        try:
                            if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                self.done = True
                                sys.exit()
                            elif event.type == pg.MOUSEBUTTONDOWN:
                                if self.midLeft.collidepoint(event.pos):
                                    files = []
                                    for item in self.sensorList:
                                        file2 = item.fileName[:-4]
                                        files.append(file2 + "_log.csv")
                                    self.emailer.sendLogData(addressList, files)
                                elif self.midRight.collidepoint(event.pos):
                                    self.done = True
                                    sys.exit()
                                elif self.backBtn.collidepoint(event.pos):
                                    return
                        except:
                            continue

    # Settings
    def settings_event(self):
        while(1):
            if(self.readingNow == False):
                self.settings_event_screen()
                pg.display.update()
                pg.event.clear()
                pg.event.wait()
                if(self.readingNow == False):
                    for event in pg.event.get():
                        try:
                            if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                self.done = True
                                sys.exit()
                            elif event.type == pg.MOUSEBUTTONDOWN:
                                if self.topRight.collidepoint(event.pos):
                                    self.createSensors()
                                elif self.btmLeft.collidepoint(event.pos):
                                    self.numpad_event("Enter Days Stored", "", 4)
                                elif self.btmRight.collidepoint(event.pos):
                                    self.numpad_event("Enter Reads/Day", "", 3)
                                elif self.backBtn.collidepoint(event.pos):
                                    return
                                elif self.settingsBtn.collidepoint(event.pos):
                                    self.advanced_settings_event()
                        except:
                            continue

    # Numpad
    def numpad_event(self, lowUp, ulrange, cal):
        newValue = ""
        self.numpad_event_screen(lowUp, ulrange, cal)
        color = pg.Color("yellow")
        while(1):
            if(self.readingNow == False):

                try:
                    pg.display.update() 
                    myfont = pg.font.SysFont("monospace", 15)
                    value = myfont.render(newValue, 1, color)
                    self.viewScreen.blit(value, (5,215))
            
                    pg.display.update()
                    pg.event.clear()
                    pg.event.wait()
                    if(self.readingNow == False):
                        for event in pg.event.get():
                                if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                    self.done = True
                                    sys.exit()
                                elif event.type == pg.MOUSEBUTTONDOWN:
                                    if self.one.collidepoint(event.pos):
                                        newValue = newValue + "1"
                                    elif self.two.collidepoint(event.pos):
                                        newValue = newValue + "2"
                                    elif self.three.collidepoint(event.pos):
                                        newValue = newValue + "3"
                                    elif self.four.collidepoint(event.pos):
                                        newValue = newValue + "4"
                                    elif self.five.collidepoint(event.pos):
                                        newValue = newValue + "5"
                                    elif self.six.collidepoint(event.pos):
                                        newValue = newValue + "6"
                                    elif self.seven.collidepoint(event.pos):
                                        newValue = newValue + "7"
                                    elif self.eight.collidepoint(event.pos):
                                        newValue = newValue + "8"
                                    elif self.nine.collidepoint(event.pos):
                                        newValue = newValue + "9"
                                    elif self.period.collidepoint(event.pos):
                                        newValue = newValue + "."
                                    elif self.zero.collidepoint(event.pos):
                                        newValue = newValue + "0"
                                    elif self.deleteBtn.collidepoint(event.pos):
                                        newValue = newValue[:-1]
                                        self.viewScreen.fill((0,0,0))
                                        self.numpad_event_screen(lowUp, ulrange, cal)
                                    elif self.submitBtn.collidepoint(event.pos):
                                                if cal is 0:
                                                    cfg[ulrange][str(self.sensor)] = newValue
                                                    for part in self.sensorList:
                                                        if part.sensorTag == self.sensor:
                                                            if ulrange == "lowRange":
                                                                if float(newValue) < float(part.highRange) and float(newValue) > 0:
                                                                    part.lowRange = newValue
                                                                    with open("/home/pi/FishCode/Configure.yaml", "w") as f:
                                                                        yaml.dump(cfg, f)
                                                            else:
                                                                if float(newValue) > float(part.lowRange) and float(newValue) > 0:
                                                                    part.highRange = newValue
                                                                    with open("/home/pi/FishCode/Configure.yaml", "w") as f:
                                                                        yaml.dump(cfg, f)
                                                elif cal is 3:
                                                    if int(newValue) > 0:
                                                        cfg["readsPerDay"]["reads"] = newValue
                                                        self.readsPerDay = newValue
                                                        self.update_reads_per_day()
                                                        for part in self.sensorList:
                                                            part.readsPerDay = newValue
                                                    with open("/home/pi/FishCode/Configure.yaml", "w") as f:
                                                        yaml.dump(cfg, f)
                                                elif cal is 4:
                                                    if int(newValue) > 0:
                                                        cfg["daysStored"]["days"] = newValue
                                                        self.daysToKeep = newValue
                                                        for part in self.sensorList:
                                                            part.daysToKeep = newValue
                                                    with open("/home/pi/FishCode/Configure.yaml", "w") as f:
                                                        yaml.dump(cfg, f)
                                                else:
                                                    self.calNum = newValue
                                                return
                                    elif self.backBtn.collidepoint(event.pos):
                                        return
                except:
                    continue
            else:
                self.numpad_event_screen(lowUp, ulrange, cal)

    # Update Probe
    def update_event(self, sensorName, sensorTag, sensor):
        while(1):
            if(self.readingNow == False):
                try:
                    self.update_event_screen(sensorName, sensorTag, sensor)
                    pg.display.update()
                    pg.event.clear()
                    pg.event.wait()
                    if(self.readingNow == False):
                        for event in pg.event.get():
                                if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                    self.done = True
                                    sys.exit()
                                elif event.type == pg.MOUSEBUTTONDOWN:
                                    if self.btmLeftSmall.collidepoint(event.pos):
                                        self.sensor = sensorTag
                                        self.numpad_event("Low", "lowRange", 0)
                                    elif self.middleBtnSmall.collidepoint(event.pos):
                                        try:
                                            self.viewScreen.fill((0,0,0))
                                            color = pg.Color("steelblue1")
                                            myfont = pg.font.SysFont("monospace", 15)
                                            takeReadsText = myfont.render("Taking Reads...", 1, color)
                                            takeReadsTextpos = takeReadsText.get_rect()
                                            takeReadsTextpos.centerx = self.background.get_rect().centerx
                                            takeReadsTextpos.centery = self.background.get_rect().centery
                                            self.viewScreen.blit(takeReadsText, takeReadsTextpos)
                                            pg.display.update()
                                        except:
                                            continue
                                        try:
                                            reads = sensor.takeRead()
                                            reads = reads[:-1]
                                            [float(i) for i in reads]
                                            avgRead = sum(reads) / len(reads)
                                            avgRead2 = round(avgRead,1)
                                            sensor.currRead = str(avgRead2)
                                        except:
                                            continue
                                        self.viewScreen.fill((0,0,0))
                                        self.update_event_screen(sensorName, sensorTag, sensor)
                                    elif self.topLeft.collidepoint(event.pos):
                                        if sensorTag is "DO":
                                            if(self.dOxygen.i2cAddress != -1):
                                                self.dOxygen_calibrate()
                                        elif sensorTag is "PH":
                                            if(self.ph.i2cAddress != -1):
                                                self.pH_calibrate()
                                        elif sensorTag is "T":
                                            if(self.temperature.i2cAddress != -1):
                                                self.temp_calibrate()
                                        elif sensorTag is "EC":
                                            if(self.conductivity.i2cAddress != -1):
                                                self.cond_calibrate()
                                    elif self.topRight.collidepoint(event.pos):
                                        if sensorTag is "DO":
                                            self.createdOxygenSensor()
                                        elif sensorTag is "PH":
                                            self.createPHSensor()
                                        elif sensorTag is "T":
                                            self.createTemperatureSensor()
                                        elif sensorTag is "EC":
                                            self.createConductivitySensor()
                                        self.viewScreen.fill((0,0,0))
                                        self.update_event_screen(sensorName, sensorTag, sensor)
                                    elif self.btmRightSmall.collidepoint(event.pos):
                                        self.sensor = sensorTag
                                        self.numpad_event("High", "highRange", 0)
                                    elif self.backBtn.collidepoint(event.pos):
                                        return
                except:
                    continue

    # Switches between the event loops depending on button pressed  
    def main_loop(self):
        while(self.done == False):
            if(self.readingNow == False):
                try:

                    self.main_menu_screen()
                    pg.display.update()
                    pg.event.clear()  
                    pg.event.wait() 
                    if(self.readingNow == False):
                        for event in pg.event.get():
                            if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                                self.done = True
                                sys.exit()
                            if event.type == pg.MOUSEBUTTONDOWN:
                                if self.topLeft.collidepoint(event.pos):
                                    self.update_event("Conductivity", "EC", self.conductivity)
                                elif self.topRight.collidepoint(event.pos):
                                    self.update_event("dOxygen", "DO", self.dOxygen)
                                elif self.btmRight.collidepoint(event.pos):
                                    self.update_event("Temperature", "T", self.temperature)
                                elif self.btmLeft.collidepoint(event.pos):
                                    self.update_event("pH", "PH", self.ph)
                                elif self.settingsBtn.collidepoint(event.pos):
                                    self.settings_event()
                except:
                    continue

# Initializes pygame and starts touchscreen loop
def main():
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    pg.init()
    pg.display.set_caption(CAPTION)
    pg.display.set_mode(SCREEN_SIZE)
    #TESTING pg.display.toggle_fullscreen()
    App().main_loop()
    pg.quit()
    sys.exit()

if __name__ == "__main__":
    main()

#TODO - create try-catch in functions to prevent crashing
#TODO - screen sleeps after a minute of time unused
#           add a thread that is a timer, somehow combine with main and go into this function:
#           add a black screen that tests if user has hit the screen (one button), return to previous activity if it has
#           creates a new thread timer when screen is touched
#TODO - check if website updates, update sensor objects (this should work now)
#TODO - limit character size for number input
#TODO - clean up code

#tODO - create an error log, remove all print statements
#TODO create classes
#TODO create linear reading for calibration screens (simpler to understand)
#TODO boot on start (redo, no longer works...)
#TODO move all screen references into screen class, easier to read TouchScreen class
#TODO determine information that needs to be passed and add that to function passing rather than global

#TODO Thanksgiving
#TODO - Calibration - add all variations of calibration, test that current ones work still, split all calibrations into screen and loop
# temp functions, could be cleaner, still needs refresh of screen returning from checktime taking reads
# ph
# do
# cond
#TODO overhaul the numpad self.calNum to just return the calNum instead of passing it globally, easier in some parts

#TODO - create note that our server will only take up to 6 months worth of data if taking one read an hour
#  ask about if we should do a limit to 6 months size if they change reads per day less than 24
#  if the user changes the reads per day to be less than 24, could they still have data loaded onto the 
#  server for the amount of 6 months, or should I limit the data to be whatever 6 months is worth
#TODO - check login and post readings to website correctly
#TODO - Take pictures with instructions
#TODO - ask about putting in a minimum for the number of reads per day at 1 per hour
