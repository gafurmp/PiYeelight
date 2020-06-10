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


