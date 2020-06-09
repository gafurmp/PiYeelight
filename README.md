# Yeelight smart bulb controller:

This python package provides methods to controll Yeelight smart bulb.

# Installation:

Clone or cownload this package and run **"pip install ."** from root of this package to install.

# Example Usecase: 


**Pre-Conditions:**

  - Raspberry Pi
  - Install python3
  - Yeelight smart bulb
  - Download Yeelight app from Apple Store or Googleplay and enable "LAN Control"
    Select your device -> goto More -> enable LAN Control
    
**Enable Auto-run while start-up:**


   Edit rc.local - sudo nano /etc/rc.local
   Enter the below line to the end of the file before exit 0
   sudo python /etc/myGit/yeelightCtrl.py &

**Common Errors:**


Error: socket.error: [Errno 98] Address already in use.
Reason: This error will come if the cocket is already in use. for e.g. killed the python script without closing the socket.
Solution: Kill the already running instance of the program since the socket is already in use.

sudo kill -9 $(ps aux | grep '[p]ython /path/to/main/yeelight_main.py' | awk '{print $2}')
