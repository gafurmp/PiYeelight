##!/usr/bin/python

'''
Import modules
'''
import socket
import time
import fcntl
import re
import os
import errno
import struct
import signal
import sys
from collections import OrderedDict
import logging
from time import sleep
import datetime
import json

#log file configuration
logfile = '/var/log/YeeLight.log'

#configure logger
logging.basicConfig(filename=logfile, level=logging.DEBUG)
 
# create logger
logger = logging.getLogger('YeeLight')

MCAST_GRP = '239.255.255.250'

def get_Param_Value(data, param):
    '''
    match line of 'param = value'
    '''
    param_re = re.compile(param+":\s*([ -~]*)") #match all printable characters
    match = param_re.search(data)
    value=""
    if match != None:
      value = match.group(1)
    return value

def display_Bulbs(bulbs, idx2ip):
    '''
    Displays all detected bulbs
    bulbs: dictionary of detected bulbs
    idx2ip: list of detected devices
    '''
    print(str(len(bulbs)) + " managed bulbs")
    for i in range(1, len(bulbs)+1):
       if not idx2ip.has_key(i):
          time = datetime.datetime.now()
          logger.debug("{0}:".format(time))
          logger.debug("Display bulb error: invalid bulb idx")
          return
       bulb_ip = idx2ip[i]
       model = bulbs[bulb_ip][1]
       power = bulbs[bulb_ip][2]
       bright = bulbs[bulb_ip][3]
       rgb = bulbs[bulb_ip][4]
       name = bulbs[bulb_ip][5]
       port = bulbs[bulb_ip][6]
       print( str(i) + ": ip=" \
         +bulb_ip + ",model=" + model \
         +",power=" + power + ",bright=" \
         + bright + ",rgb=" + rgb\
         +",name=" +name\
         +",port=" +port)
       logger.debug( str(i) + ": ip=" \
         +bulb_ip + ",model=" + model \
         +",power=" + power + ",bright=" \
         + bright + ",rgb=" + rgb\
         +",name=" +name\
         +",port=" +port)

def BulbException(Exception):
    '''
    Modules inside this packge will raise this exception in case of any errors!
    '''
    pass
      
def discover_YeelightSmartBulbs(timeout=5, search_duration=30000):
    '''
    Discover all connected yeelight smart lights in the LAN
    timeout: timeout for socket scan, default: 5sec
    search_duration: discovery search duration, default 30sec
    '''
    search_interval=search_duration
    read_interval=100
    time_elapsed=0
  
    scan_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    fcntl.fcntl(scan_socket, fcntl.F_SETFL, os.O_NONBLOCK)
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.bind(("", 1982))
    fcntl.fcntl(listen_socket, fcntl.F_SETFL, os.O_NONBLOCK)
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    scan_socket.settimeout(timeout)
    
    detected_bulbs = {}
    bulb_idx2ip = {}
    RUNNING = True
    
    while RUNNING:
       if time_elapsed%search_interval == 0:
           multicase_address = (MCAST_GRP, 1982) 
           msg = "M-SEARCH * HTTP/1.1\r\n" 
           msg = msg + "HOST: 239.255.255.250:1982\r\n"
           msg = msg + "MAN: \"ssdp:discover\"\r\n"
           msg = msg + "ST: wifi_bulb"
           scan_socket.sendto(msg, multicase_address)
           time = datetime.datetime.now()
           logger.debug("{0}:".format(time))
           logger.debug("Discovering bulbs- Send search request: " + msg)
           
           #scan for responses
           while True:
            try:
                data = scan_socket.recv(2048)
                if data is not '':
                  logger.debug("response recieved: " + data)
                  location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
                  match = location_re.search(data)
                  if match != None:      
                     host_ip = match.group(1)
                     if detected_bulbs.has_key(host_ip):
                        bulb_id = detected_bulbs[host_ip][0]
                     else:
                        bulb_id = len(detected_bulbs)+1
                     host_port = match.group(3)
                     
                     model = get_Param_Value(data, "model")
                     power = get_Param_Value(data, "power")
                     bright = get_Param_Value(data, "bright")
                     rgb = get_Param_Value(data, "rgb")
                     name = get_Param_Value(data, "name")
                     
                     # use two dictionaries to store index->ip and ip->bulb map
                     detected_bulbs[host_ip] = [bulb_id, model, power, bright, rgb, name, host_port]
                     bulb_idx2ip[bulb_id] = host_ip
                     
                     RUNNING = False
            except socket.timeout:
                logger.debug("Socket Timeout")
                break
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                   logger.debug("discover_YeelightSmartLights Scan Socket - Error: "+ str(e))
                   break
                else:
                   logger.debug("discover_YeelightSmartLights Scan Socket - Exit: " + str(e))
                   sys.exit(1)

           #listen for for responses
           while True:
            try:
                data, addr = listen_socket.recvfrom(2048)
                if data is not '':
                  logger.debug("response recieved: " + data)
                  location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
                  match = location_re.search(data)
                  if match != None:              
                     host_ip = match.group(1)
                     if detected_bulbs.has_key(host_ip):
                        bulb_id = detected_bulbs[host_ip][0]
                     else:
                        bulb_id = len(detected_bulbs)+1
                     host_port = match.group(3)
                     
                     model = get_Param_Value(data, "model")
                     power = get_Param_Value(data, "power")
                     bright = get_Param_Value(data, "bright")
                     rgb = get_Param_Value(data, "rgb")
                     name = get_Param_Value(data, "name")
                      
                     # use two dictionaries to store index->ip and ip->bulb map
                     detected_bulbs[host_ip] = [bulb_id, model, power, bright, rgb, name, host_port]
                     bulb_idx2ip[bulb_id] = host_ip
                     
                     RUNNING = False
            except socket.timeout:
                logger.debug("Socket Timeout")
                break
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                   logger.debug("discover_YeelightSmartLights Passive Listner - Error: "+ str(e))
                   break
                else:
                   logger.debug("discover_YeelightSmartLights Passive Listner - Exit: " + str(e))
                   sys.exit(1)
           
       time_elapsed+=read_interval
       sleep(read_interval/1000.0)             
        
    scan_socket.close()
    listen_socket.close()
    
    return detected_bulbs, bulb_idx2ip

class SmartBulb(object):
  """
  SmartBulb class, which provides methods to control different aspects of yeelight smart bulb.
  """
  def __init__(self, ip, port=55443, power='off', rgb=16777215, duration=300, model='color', effect="smooth", bright=0, name=''):
    '''
    Initialise SmartBulb object.
    ip: ipv4 addr of device
    port: detected port of device for comunication
    power: Current status of the device ('on', 'off')
    rgb: Current rgb value of the bulb display (decimal from 0 to 16777215)
    model: model of the device ("mono","color", "stripe", "ceiling", "bslamp")
    effect: transition effect ("smooth", "sudden")
    bright: Current brightness in percentage (0-100 in decimal)
    name: Configured name of the device
    '''
    self._ip = ip
    self._port = port
    self._rgb= rgb
    self._duration = duration
    self._model = model
    self._effect = effect
    self._bright= bright
    self._name = name
    self._command_id = 0
    self._lastproperties = {"power":power ,"bright":bright ,"rgb":rgb ,"model":model ,"name":name}
    self._music = 0

  def _next_Cmd_Id(self):
    self._command_id += 1
    return self._command_id

  def _operate_On_Bulb(self, method, params):
    '''
    Operate on bulb; no gurantee of success.
    Input data 'params' must be a compiled into one string.
    E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
    '''
    bulb_ip=self._ip
    port=self._port
    
    if ( (self._music != 1) or (method == "set_music") ):
       try:
           time = datetime.datetime.now()
           logger.debug("{0}:".format(time))
           tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
           logger.debug("connect "+ bulb_ip+ str(port) +"...")
           tcp_socket.connect((bulb_ip, int(port)))
           msg="{\"id\":" + str(self._next_Cmd_Id()) + ",\"method\":\""
           msg += method + "\",\"params\":[" + params + "]}\r\n"
           tcp_socket.send(msg)
           logger.debug(msg)
           
           response = None
           
           #scan for responses
           while response is None:
                data = tcp_socket.recv(2048)
                if data is not "":
                   logger.debug("response recieved: " + data)
                   response = json.dumps(data) # to string
                   responsedict = json.loads(data) #to dict
                   if "result" in responsedict:
                       resultlist = responsedict["result"]
                       if method == 'get_prop':
                           self._lastproperties = {"power":str(resultlist[0]) ,"bright":str(resultlist[1]) ,"rgb":str(resultlist[2]) ,"model":str(resultlist[3]) ,"name":str(resultlist[4])}
           return self._lastproperties
      
       except socket.error as e:
           logger.debug("Unexpected error: {0}".format(e))
       finally:
           tcp_socket.close()
    else:
        logger.debug("Music mode ON. Request can not be processed")

  def toggle(self):
    '''
    Toggles bulb's status
    '''
    self._operate_On_Bulb("toggle", "")

  def set_name(self, name):
    '''
    Sets bulb's name
    name: name of bulb
    '''
    self._operate_On_Bulb("set_name", "\""+name+"\"")
    
  def set_bright(self, bright):
    '''
    Sets bulb's brightness
    bright: brightness in percentage
    '''
    self._operate_On_Bulb("set_bright", str(bright))

  def set_power(self, power):
    '''
    Sets bulb's target power status
    power: on/ off
    '''
    method="set_power"
    if power == "off":
      params="\"off\",\"smooth\",500"
    else:
      params="\"on\",\"smooth\",500"
    self._operate_On_Bulb(method, params)

  def get_prop(self, requested_properties =["power","bright","rgb","model","name"]):
    '''
    Gets bulb requested properties color, model, brightness, name and power.
    '''
    method="get_prop"
    params="\""
    for property in requested_properties:
       params += property + "\",\""
    params += "not_exist\""
    
    properties = self._operate_On_Bulb(method, params)
    
    return properties

  def set_ct_abx(self, ct = '1700', effect = 'smooth'):
    '''
    Sets the color temperature of a smart LED.
    ct: target color temperature (1700 ~ 6500)
    effect: Transition (smooth/ or sudden)
    '''
    method="set_ct_abx"
    params=str(ct) + ",\"" + effect + "\",500"
    self._operate_On_Bulb(method, params)
    
  def set_rgb(self, rgb = '16777215', effect = 'smooth'):
    '''
    Sets the color of a smart LED.
    rgb: target rgb (1700 ~ 6500)
    effect: Transition (smooth/ or sudden)
    '''
    method="set_rgb"
    params=str(rgb) + ",\"" + effect + "\",500"
    self._operate_On_Bulb(method, params)

  def set_hsv(self, hue = '255', sat='45', effect = 'smooth'):
    '''
    Sets the color of a smart LED.
    "hue": target hue value, whose type is integer. It should be expressed in decimal integer ranges from 0 to 359.
    "sat": target saturation value whose type is integer. It's range is 0 to 100.
    effect: Transition (smooth/ or sudden)
    '''
    method="set_hsv"
    params=str(hue) + "," + str(sat) + ",\"" + effect + "\",500"
    self._operate_On_Bulb(method, params)
    
  def set_default(self):
    '''
    Saves current state of smart LED in persistent memory
    Not supported by all devices
    '''
    method="set_default"
    params=""
    self._operate_On_Bulb(method, params)
    
  def start_cf(self, count, action, flow_expression):
    '''
    Starts a color flow. Color flow is a series of smart.
    LED visible state changing. It can be brightness changing, color changing or color temperature changing
    count: is the total number of visible state changing before color flow stopped. 0 means infinite loop on the state changing.
    action: is the action taken after the flow is stopped.
    0 means smart LED recover to the state before the color flow started.
    1 means smart LED stay at the state when the flow is stopped.
    2 means turn off the smart LED after the flow is stopped.
    flow_expression: is the expression of the state changing series (as string)
    '''     
    method="start_cf"
    params= str(count) + ","+ str(action) + "," + ",\"" + flow_expression + "\""
    self._operate_On_Bulb(method, params)
     
  def stop_cf(self):
    '''
    Stops a running color flow
    '''     
    method="stop_cf"
    params=""
    self._operate_On_Bulb(method, params)  
     
  def set_scene(self, _class):
    '''
    Sets the smart LED directly to specified state
    _class: can be "color", "hsv", "ct", "cf", "auto_dealy_off". "color" means change the smart LED to specified color and brightness
    Pass the parameter as string of commands.
    e.g. "\"color\", 65280, 70"
    "\"hsv\", 300, 70, 100"
    
    '''     
    method="set_scene"
    params= _class
    self._operate_On_Bulb(method, params)  
     
  def cron_add(self, _type, value):
    '''
    Starts a timer job on the smart LED
    _type: currently can only be 0  (means power off)
    value: is the length of the timer (in minutes)
    '''     
    method="cron_add"
    params=str(_type) + "," + str(value)
    self._operate_On_Bulb(method, params)  
     
  def cron_get(self, _type):
    '''
    Retrieves the setting of the current cron job of the specified type
    _type: the type of the cron job. (currently only support 0)
    '''     
    method="cron_get"
    params=str(_type)
    self._operate_On_Bulb(method, params)  
     
  def cron_del(self, _type):
    '''
    Stops the specified cron job
    _type: the type of the cron job. (currently only support 0)
    '''     
    method="cron_del"
    params=str(_type)
    self._operate_On_Bulb(method, params)  

  def set_adjust(self, action, prop):
    '''
    Changes brightness, CT or color of a smart LED without knowing the current value, it's main used by controllers.
    action: the direction of the adjustment. The valid value can be:
    "increase": increase the specified property
    "decrease": decrease the specified property
    "circle": increase the specified property, after it reaches the max
    prop: the property to adjust. The valid value can be:
    "bright": adjust brightness.
    "ct": adjust color temperature.
    "color": adjust color. (When "prop" is "color", the "action" can only be "circle", otherwise, it will be deemed as invalid request.)
    '''     
    method="set_adjust"
    params="\"" + action + "\",\"" + prop + "\""
    self._operate_On_Bulb(method, params)  
     
  def adjust_bright(self, percentage):
    '''
    Adjusts the brightness by specified percentage within specified duration.
    percentage: the percentage to be adjusted. The range is: -100 ~ 100
    '''     
    method="adjust_bright"
    params= str(percentage)+",500"
    self._operate_On_Bulb(method, params)  
     
  def adjust_ct(self, percentage):
    '''
    Adjusts the color temperature by specified percentage within specified duration.
    percentage: the percentage to be adjusted. The range is: -100 ~ 100
    '''     
    method="adjust_ct"
    params= str(percentage)+",500"
    self._operate_On_Bulb(method, params)  
     
  def adjust_color(self, percentage):
    '''
    Adjusts the color  by specified percentage within specified duration.
    percentage: the percentage to be adjusted. The range is: -100 ~ 100
    '''     
    method="adjust_color"
    params= str(percentage)+",500"
    self._operate_On_Bulb(method, params)  
     
  def set_music (self, action, host, port):
    '''
    Starts or stop music mode on a device. Under music mode, no property will be reported and no message quota is checked.
    action: the action of set_music command. The valid value can be:
    0: turn off music mode.
    1: turn on music mode.
    host: the IP address of the music server as string.
    port: the TCP port music application is listening on.
    '''     
    method="set_music"
    params= str(action) + ",\"" + host + "\","+str(port)
    self._music = action
    self._operate_On_Bulb(method, params)  
