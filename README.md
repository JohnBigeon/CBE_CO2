# CBE_CO2

<p float="center">
  <img src="https://github.com/JohnBigeon/CBE_CO2/blob/main/Pictures/plot.png" />
</p>


## Introduction
Here, we will build/assemble a device to measure environmental parameters such as:
- temperature, 
- CO2 concentration,
- Volatile Organic Compounds (VOC) cocentration
- Temperature
- Humidity
- Pression

This device consists of a microcontroller (ESP32), a BME280 chip and a CCS811 chip.

## Concept

From a practical view, the environmental information is obtained by a the small chip and then saved on a micro SD-card. The remote access is achieved using the websocket protocol.

## Hardware & Integration
### Wiring

```
ESP32        BME280    CCS811    SD card reader
----------   -------   --------  --------------
       3V3 - Vin     - Vcc
       GND - GND     - GND      - GND
        V5 -         -          - Vcc
       G23 -         -          - MOSI
       G22 -         - SCL
       G21 -         - SDA
       GND -         - WAK
       G19 -         -          - MISO
       G18 -         -          - SCK
        G5 -         -          - CS
       G33 - SDA
       G32 - SCL 
```

![KiCad](https://github.com/JohnBigeon/CBE_CO2/blob/main/KiCad_files/schematic.png)

![PCB](https://github.com/JohnBigeon/CBE_CO2/blob/main/KiCad_files/pcb.png)

### First integration
![Integration](https://github.com/JohnBigeon/CBE_CO2/blob/main/Pictures/integration_v01.jpg)

### Price
```
         Object           Price (€)
-----------------------   -----
       AZDelivery ESP32 - 18
                 BME280 - 0 
                 CCS811 - 10
                 Cables - 1
```
## Software
## ESP32 with micropython
### Flashing the ESP32 to install micropython
On Anaconda, create an anaconda environment and install esptool:
```
conda create --name pyesp32 python=3.9.13
conda activate pyesp32
pip install esptool
```
Check if everything is working:
```
esptool.py version
```
If you are on Windows:
```
esptool version
```
To check the version of your board:
Press the boot button and enter the following command:
```
esptool.py chip_id
esptool.py v4.4
Found 2 serial ports
Serial port /dev/ttyUSB0
Connecting..............
Detecting chip type... Unsupported detection protocol, switching and trying again...
Connecting....
Detecting chip type... ESP32
Chip is ESP32-D0WD-V3 (revision v3.0)
Features: WiFi, BT, Dual Core, 240MHz, VRef calibration in efuse, Coding Scheme None
Crystal is 40MHz
MAC: XXX
Uploading stub...
Running stub...
Stub running...
Warning: ESP32 has no Chip ID. Reading MAC instead.
MAC: XXX
Hard resetting via RTS pin...
```
#### If ESP32 is not recognized
USB drivers missing
https://www.silabs.com/documents/public/software/CP210x_Windows_Drivers.zip

Download the firmware on the website here [https://micropython.org/download/esp32-ota/].

```
esptool.py --port /dev/ttyUSB0 erase_flash
```
```
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-20180511-v1.9.4.bin
```

## First connection
### SD card

To be able to connect to the wifi, you should update the wifi credentials on the SD card as 
```
ssid = <your wifi SSID>
password = <password>
```


### Websocket connection
The IP's address of your device is saved on the SD card in the file params.txt:
```
network config: ('XXX.XXX.XXX.XX', ...)
```

Then, test the connection with the device using your laptop or smartphone:
![Check_connection](https://github.com/JohnBigeon/CBE_CO2/blob/main/Pictures/record.png)

### Full measurement
Measurement are saved on the SD card as:
```
Date(ISO 8601), Time(s), CO2 (ppm), VOC (ppb), Temp (degC), hum (%), pressure (hPa)
2023-04-30T12:06:33.000Z, 736171593, 470, 9, 21.28, 50.13, 1009.03
2023-04-30T12:06:35.000Z, 736171595, 470, 9, 21.28, 50.19, 1009.14
2023-04-30T12:06:37.000Z, 736171597, 464, 9, 21.29, 50.15, 1009.11
2023-04-30T12:06:39.000Z, 736171599, 476, 10, 21.28, 50.15, 1009.14
2023-04-30T12:06:41.000Z, 736171601, 470, 12, 21.27, 50.15, 1009.11
2023-04-30T12:06:43.000Z, 736171603, 486, 12, 21.28, 50.15, 1009.14
2023-04-30T12:06:45.000Z, 736171605, 486, 10, 21.27, 50.1, 1009.03
2023-04-30T12:06:47.000Z, 736171607, 486, 13, 21.27, 50.07, 1009.11
2023-04-30T12:06:49.000Z, 736171609, 491, 13, 21.26, 50.08, 1009.11
2023-04-30T12:06:51.000Z, 736171611, 496, 13, 21.26, 50.09, 1009.14
2023-04-30T12:06:53.000Z, 736171613, 496, 14, 21.26, 50.1, 1009.14
```
The date is following the ISO8601 format. 
## Micropython code
### Main
```
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
```

### Well-known bugs
#### 
    
### Future improvements
* Use battery as power supply ?
* Use a Bluetooth module to replace the wired connection for transmitting serial data.
* Not able to connect to Wifi requiring a login and a password.
