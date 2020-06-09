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
    
**Enable Auto-run while start-up:**<br>
   Edit rc.local - sudo nano /etc/rc.local<br>
   Enter the below line to the end of the file before exit 0<br>
   sudo python /path/to/main/yeelight_main.py &<br>

**Common Errors:**<br>
**Error:** socket.error: [Errno 98] Address already in use.<br>
**Reason:** This error will come if the cocket is already in use. for e.g. killed the python script without closing the socket.<br>
**Solution:** Kill the already running instance of the program since the socket is already in use.<br>
sudo kill -9 $(ps aux | grep '[p]ython /path/to/main/yeelight_main.py' | awk '{print $2}')<br>
