#!/usr/bin/python3.4
import smtplib, email
import socket, struct, fcntl
import time
from email.mime.text import MIMEText
from email import *
import os, sys, re
import requests
from subprocess import check_output

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockfd = sock.fileno()
SIOCGIFADDR = 0x8915

class Emailer(object):
    def warning(self, data, recipients, sensor):
        message = "The " + str(sensor) + " sensor is not working correctly."
        subject = 'Sensor isn\'t working'
        self.sendEmail(data, recipients, message, subject)

    def sendIP(self, data, recipients):
        message = "zfish1 is up and running at (wired, wireless): "
        subject = 'Fish monitor running'
        self.sendEmail(data, recipients, message, subject)

    def sendEmail(self, data, recipients, message, subject):
        try:
            //TODO add your email and password here
            SMTP_SERVER = 'smtp.gmail.com'
            SMTP_PORT = 587
            SMTP_USERNAME = //your email username
            SMTP_PASSWORD = //your email password
            SMTP_FROM = //the email sends from this address

            for address in recipients:
                SMTP_TO = address
                mailer = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                mailer.ehlo()
                mailer.starttls()
                mailer.login(SMTP_USERNAME, SMTP_PASSWORD)

                compiledMsg = message + " \n".join(data)

                msg = MIMEText(compiledMsg, 'plain')
                msg['Subject'] = subject
                msg['To'] = SMTP_TO
                msg['From'] = SMTP_FROM

                mailer.send_message(msg)
                mailer.quit()
        except Exception as e:
            print("Did not send email")
    
                
    def get_interface_ipaddress(self, network):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', bytes(network[:15], 'utf-8'))
        )[20:24])

    def getIP(self, iface):
        netw = iface.encode('utf-8')
        ifreq = struct.pack('16sH14s', iface, socket.AF_INET, '\x00'*14)
        netw = ifreq.encode('utf-8')
        try:
            res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
        except:
            return "None"
        ip = struct.unpack('16sH2x4s8x', res)[2]
        return str(socket.inet_ntoa(ip))