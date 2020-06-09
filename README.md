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
    Select your device -> goto More -> enable LAN Control
**yeelight_main.py:**<br>
~~~
from yeelight import YeeLight
import datetime
from threading import Thread
from time import sleep
import sys

def main():
  # create yeelight bulb object
  bulb = YeeLight('ENABLE')

  # detect yeelight bulbs
  bulb.send_Search_Broadcast()

  # scan post for response
  bulb.scan_Broadcast_Response()

  timeout = 1
  
  while True:
    try:
      print(bulb.is_Bulbs_Detected())
      if (bulb.is_Bulbs_Detected() == False):
        #listen on socket passivly
        bulb.listen_Socket_Passive()
      else:
        timeout = 60
        bulb.display_Bulbs()
        bulb.toggle_BulbState(1)
    except NameError as e:
      print("Opps.. Error detected: {0}".format(e))
    except:
      print("Something went wrong!", sys.exc_info()[0])
    finally:
      sleep(timeout)
     

if __name__=='__main__':
  main()
~~~
**Enable Auto-run while start-up:**<br>
   Edit rc.local - sudo nano /etc/rc.local<br>
   Enter the below line to the end of the file before exit 0<br>
   sudo python /path/to/main/yeelight_main.py &<br>

**Common Errors:**<br>
**Error:** socket.error: [Errno 98] Address already in use.<br>
**Reason:** This error will come if the cocket is already in use. for e.g. killed the python script without closing the socket.<br>
**Solution:** Kill the already running instance of the program since the socket is already in use.<br>
sudo kill -9 $(ps aux | grep '[p]ython /path/to/main/yeelight_main.py' | awk '{print $2}')<br>
