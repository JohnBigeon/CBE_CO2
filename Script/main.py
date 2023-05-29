# -*- coding: utf-8 -*-
"""
Created on Sun Jan 22 13:13:42 2023

@author: JBI
"""

"""
###############################################
##Title             : main.py
##Description       : Main script for CBE-CO2 project
##Author            : John Bigeon   @ Github
##Date              : 20230122
##Version           : Test with 
##Usage             : MicroPython (esp32-20220618-v1.19.1)
##Script_version    : 0.0.5 (not_release)
##Output            : 
##Notes             :
###############################################
"""
###############################################
### Package
###############################################
from microWebSrv import MicroWebSrv
import time
import machine
import utime
from utime import localtime
import ntptime
import network
import socket
from machine import Pin, I2C, SoftI2C, SDCard
import CCS811
import json
import uos
import os
import re
import BME280

###############################################
### Function: JSON
###############################################
def importFile_to_JSON(file):
    max_len = 27  # maximum number of lines in content variable
    timus, dat_CO2, dat_VOC, dat_temp, dat_hum, dat_pres = [], [], [], [], [], []

    with open(file, 'r') as fp:
        num_lines = sum(1 for line in fp)  # count the total number of lines in the file
        step = max(1, num_lines // max_len)  # calculate the step value based on the file length
        fp.seek(0)  # reset the file pointer to the beginning of the file

        for i, line in enumerate(fp):
            if i % step == 0 and i > 0:  # check if the current line should be extracted
                tempList = line.strip().split(',')
                timus.append(str(tempList[0]))
                #timus_sec.append(int(tempList[1]))
                dat_CO2.append(float(tempList[2]))
                dat_VOC.append(float(tempList[3]))
                dat_temp.append(float(tempList[4]))
                dat_hum.append(float(tempList[5]))
                dat_pres.append(float(tempList[6]))
                if len(timus) >= max_len:  # check if the maximum length has been reached
                    break  # stop processing the file

    # Remove dummy 
    if timus and timus[-1] == '':
        timus.pop()
    #if timus_sec and timus_sec[-1] == '':
    #    timus_sec.pop()
    if dat_CO2 and dat_CO2[-1] == '':
        dat_CO2.pop()
    if dat_VOC and dat_VOC[-1] == '':
        dat_VOC.pop()
    if dat_temp and dat_temp[-1] == '':
        dat_temp.pop()
    if dat_hum and dat_hum[-1] == '':
        dat_hum.pop()
    if dat_pres and dat_pres[-1] == '':
        dat_pres.pop()

    graph_to_send = json.dumps({'timus':timus, 'dat_CO2':dat_CO2, 'dat_VOC':dat_VOC, 'dat_temp':dat_temp, 'dat_hum':dat_hum, 'dat_pres':dat_pres})
    return graph_to_send
    
    
###############################################
### Class: CCS811
###############################################
class gaz_sensor:
    def __init__(self):
        self.i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
        self.sens = CCS811.CCS811(i2c=self.i2c, addr=90) # Adafruit sensor breakout has i2c addr: 90; Sparkfun: 91

    def read(self):
        while True:
            try:
                if self.sens.data_ready():
                    return {'val_CO2': self.sens.eCO2, 'val_VOC': self.sens.tVOC}
            except:
                pass
            

###############################################
### Class: BME280
###############################################          
def read_env_sensor():
    i2c = SoftI2C(scl=Pin(32), sda=Pin(33), freq=10000)
    bme = BME280.BME280(i2c=i2c, address=118)
    temp = float(bme.temperature)
    hum = float(bme.humidity)
    pres = float(bme.pressure)
    return {'val_temp': temp, 'val_hum': hum, 'val_pres' : pres}

class env_sensor:
    def __init__(self):
        self.i2c = SoftI2C(scl=Pin(32), sda=Pin(33), freq=10000)
        self.bme = BME280.BME280(i2c=self.i2c, address=118)

    def read(self):
        temp = float(self.bme.temperature)
        hum = float(self.bme.humidity)
        pres = float(self.bme.pressure)
        return {'val_temp': temp, 'val_hum': hum, 'val_pres' : pres}
    
###############################################
### Function: Websocket
############################################### 
# Inspired by http://staff.ltam.lu/feljc/electronics/uPython/uPy_WiFi_03_websockets.pdf
def _acceptWebSocketCallback(webSocket, httpClient) :
    print("WS ACCEPT")
    webSocket.RecvTextCallback = _recvTextCallback
    ## webSocket.RecvBinaryCallback = _recvBinaryCallback
    webSocket.ClosedCallback = _closedCallback
    
def _recvTextCallback(webSocket, msg) :
    if msg == "LEDon":
        d12.on()
        
    elif msg  == "plot":
        webSocket.SendText(importFile_to_JSON(fname))
        
    elif msg == "Get":
        with open(fname, "r") as my_file:
            # read first line
            header = my_file.readline()

            # read last 200 lines
            footer = ""
            my_file.seek(0, 2) # go to the end of the file
            file_size = my_file.tell() # get the file size in bytes
            pos = max(file_size-900, 0)
            my_file.seek(pos, 0) # seek to the end minus 200 lines
            while pos < file_size:
                line = my_file.readline()
                if not line:
                    break # end of file reached
                footer += line
                pos = my_file.tell()

        print('****************************')
        header = "<br />".join(header.split("\n")) # replace \n for html communication
        footer = "<br />".join(footer.split("\n")) # replace \n for html communication
        print('****************************')
        webSocket.SendText("%s" % header)
        webSocket.SendText("%s" % footer)
        
    else:
        print('*')
        print("WS RECV TEXT : %s" % msg)
        webSocket.SendText("Reply for %s" % msg)
        
def _closedCallback(webSocket) :
    print("WS CLOSED")

def printtime():
    return('{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.000Z'.format(localtime()[0], localtime()[1], localtime()[2], localtime()[3], localtime()[4], localtime()[5]))
 
def save_data(fname, msg):
    with open(fname,'a+') as f:
        f.write(msg + '\n')
    f.close()

###############################################
### Prerequisites
###############################################
# Mount the SD card
if '/sd' not in os.listdir():
    sdcard=machine.SDCard(slot=2, sck=18, miso=19, mosi=23, cs=5, freq=19000000)
    sdcard.info()
    os.mount(sdcard, "/sd")
    print("SD card mounted successfully!")
else:
    print("SD card already mounted!")

# Extract wifi ssid and password from sdcard
wifi_credentials_loc = open("/sd/wifi_credentials.dat")
wifi_credentials = wifi_credentials_loc.read().split("\n")
wifi_credentials_ssid = wifi_credentials[0].split(" = ",1)[1]
wifi_credentials_password = wifi_credentials[1].split(" = ",1)[1]
#wifi_credentials_username = wifi_credentials[2].split(" = ",1)[1]

# Configure the ESP32 wifi
sta = network.WLAN(network.STA_IF)
if not sta.isconnected():
    print('connecting to network...')
    sta.active(True)
    sta.connect(wifi_credentials_ssid, wifi_credentials_password)
    count = 0 # initialize the counter variable
    while not sta.isconnected() and count < 25: # add the counter variable and conditional statement
        print('Not connected yet')
        count += 1 # increment the counter variable
        time.sleep(1)
        pass

    if sta.isconnected():
        print('Connected to network')
        print(sta.ifconfig())
    else:
        print('Failed to connect to network')


###############################################
### Init
###############################################
### Update timer
if sta.isconnected():
    # Set the time using NTP
    ntptime.settime()

    # Get the current UTC time
    utc_time = machine.RTC().datetime()

    # Add 1 hour to the UTC time to adjust for the Belgium time zone
    belgium_time = utc_time[0], utc_time[1], utc_time[2], utc_time[3], utc_time[4] + 1, utc_time[5], utc_time[6], utc_time[7]

    # Set the adjusted time
    machine.RTC().datetime(belgium_time)         
    
### Name of the file   
datus = '{:02d}{:02d}{:02d}{:02d}{:02d}{:02d}'.format(localtime()[0], localtime()[1], localtime()[2], localtime()[3], localtime()[4], localtime()[5])
fname = '/sd/measure_'+ datus +'.txt'
csvdata = []

###############################################
### Debug
###############################################
d12 = Pin(12, Pin.OUT)

###############################################
### Microweb
def connect_ws():
    print("Preparing server")
    srv = MicroWebSrv(webPath='www/')
    srv.WebSocketThreaded = True
    srv.AcceptWebSocketCallback = _acceptWebSocketCallback
    print("Starting server")
    srv.Start(threaded = True)
    
###############################################
### Main
###############################################
if __name__ == "__main__":
    if sta.isconnected():
        connect_ws()
        params_used = 'network config: %s' %str(sta.ifconfig())
        save_data('/sd/params.txt', params_used)
    utime_start = utime.time()
    
    gaz_sens = gaz_sensor()
    env_sens = env_sensor()
    
    save_data(fname, 'Date(ISO 8601), Time(s), CO2 (ppm), VOC (ppb), Temp (degC), hum (%), pressure (hPa)')

    try:
        while True:
            val = str("{}, {}, {}, {}, {}, {}, {}".format(printtime(), utime.time(), gaz_sens.read()['val_CO2'], gaz_sens.read()['val_VOC'], env_sens.read()['val_temp'], env_sens.read()['val_hum'], env_sens.read()['val_pres']))
            print(val)
            save_data(fname, val)
            time.sleep(1)
    except KeyboardInterrupt:
        pass

