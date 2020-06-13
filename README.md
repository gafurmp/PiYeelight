# Yeelight smart bulb controller:

This python package provides methods to controll Yeelight smart bulb.

# Installation:

Clone or cownload this package and run **"pip install ."** from root of this package to install.

# Example usecase: 

**This project need:**<br>
  - Raspberry Pi
  - Install python3
  - Yeelight smart bulb
  - Download Yeelight app from Apple Store or Googleplay and enable "LAN Control"
    Select your device -> goto More -> enable LAN Control<br>

**yeelight_main.py:** Detects YeeLight bulbs connected and toggle Idx 1 bulb between On & OFF every 1 minute.<br>
~~~
from yeelight import *
import datetime
from threading import Thread
from time import sleep
import sys

def main():
  # discover all connected bulbs on LAN
  connected_bulbs, ip2idx = discover_YeelightSmartBulbs()
  
  # create yeelight bulb object
  host_ip = ip2idx[1] # idx 1
  bulb = SmartBulb(host_ip)
  
  #toggle bulb state
  bulb.toggle()
     
if __name__=='__main__':
  main()
~~~
