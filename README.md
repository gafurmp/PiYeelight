PiYeelight
===========
Pre-Conditions:
  - Raspberry Pi
  - Install python3
  - Yeelight smart bulb
  - Download Yeelight app from Apple Store or Googleplay and enable "LAN Control"
    Select your device -> goto More -> enable LAN Control

Download the python script and run :)

Enable Auto-run while start-up:
   Edit rc.local - sudo nano /etc/rc.local
   Enter the below line to the end of the file before exit 0
   sudo python /etc/myGit/yeelightCtrl.py &

Common Error:
Error: socket.error: [Errno 98] Address already in use
Reason: This error will come if the cocket is already in use. for e.g. killed the python script without closing the socket.
Solution: Kill the already running instance of the program since the socket is already in use.

sudo kill -9 $(ps aux | grep '[p]ython yeelightCtrl.py' | awk '{print $2}')


Note: Improvements are possible and open.
