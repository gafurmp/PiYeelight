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
#import RPi.GPIO as GPIO
import signal
import datetime
from threading import Thread
from time import sleep
from collections import OrderedDict

'''
Global Constants
'''
TIMEOUT = 5 # number of seconds your want for timeout

'''
Global Variables
'''
detected_bulbs = {}
bulb_idx2ip = {}
DEBUGGING = False
RUNNING = True
current_command_id = 0
MCAST_GRP = '239.255.255.250'
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
g_ylBulbStateAct = "off"
g_ylBulbStateReq = "off"

'''
Module definitions
'''
def debug(msg):
  if DEBUGGING:
    print msg

def next_cmd_id():
  global current_command_id
  current_command_id += 1
  return current_command_id

def send_search_broadcast():
  '''
  multicast search request to all hosts in LAN, do not wait for response
  '''
  multicase_address = (MCAST_GRP, 1982) 
  debug("send search request")
  msg = "M-SEARCH * HTTP/1.1\r\n" 
  msg = msg + "HOST: 239.255.255.250:1982\r\n"
  msg = msg + "MAN: \"ssdp:discover\"\r\n"
  msg = msg + "ST: wifi_bulb"
  scan_socket.sendto(msg, multicase_address)

def bulbs_detection_loop():
  '''
  a standalone thread broadcasting search request and listening on all responses
  '''
  debug("bulbs_detection_loop running")
  search_interval=30000
  read_interval=100
  time_elapsed=0

  while RUNNING:
    if time_elapsed%search_interval == 0:
      send_search_broadcast()

    # scanner
    while True:
      try:
        data = scan_socket.recv(2048)
      except socket.error, e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            break
        else:
            print e
            #sys.exit(1)
            break
      handle_search_response(data)

    # passive listener
    while True:
      try:
        data, addr = listen_socket.recvfrom(2048)
      except socket.error, e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            break
        else:
            print e
            sys.exit(1)
            break
      handle_search_response(data)

    display_bulbs()
    time_elapsed+=read_interval
    sleep(read_interval/1000.0)
  #scan_socket.close()
  #listen_socket.close()

def get_param_value(data, param):
  '''
  match line of 'param = value'
  '''
  param_re = re.compile(param+":\s*([ -~]*)") #match all printable characters
  match = param_re.search(data)
  value=""
  if match != None:
    value = match.group(1)
    return value

def handle_search_response(data):
  '''
  Parse search response and extract all interested data.
  If new bulb is found, insert it into dictionary of managed bulbs. 
  '''
  location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
  match = location_re.search(data)
  if match == None:
    debug( "invalid data received: " + data )
    return

  host_ip = match.group(1)
  if detected_bulbs.has_key(host_ip):
    bulb_id = detected_bulbs[host_ip][0]
  else:
    bulb_id = len(detected_bulbs)+1
  host_port = match.group(3)
  model = get_param_value(data, "model")
  power = get_param_value(data, "power")
  bright = get_param_value(data, "bright")
  rgb = get_param_value(data, "rgb")
  # use two dictionaries to store index->ip and ip->bulb map
  detected_bulbs[host_ip] = [bulb_id, model, power, bright, rgb, host_port]
  bulb_idx2ip[bulb_id] = host_ip

def display_bulb(idx):
  if not bulb_idx2ip.has_key(idx):
    debug("error: invalid bulb idx")
    return
  bulb_ip = bulb_idx2ip[idx]
  model = detected_bulbs[bulb_ip][1]
  power = detected_bulbs[bulb_ip][2]
  bright = detected_bulbs[bulb_ip][3]
  rgb = detected_bulbs[bulb_ip][4]
  print str(idx) + ": ip=" \
    +bulb_ip + ",model=" + model \
    +",power=" + power + ",bright=" \
    + bright + ",rgb=" + rgb

def display_bulbs():
  print str(len(detected_bulbs)) + " managed bulbs"
  for i in range(1, len(detected_bulbs)+1):
    display_bulb(i)

def operate_on_bulb(idx, method, params):
  '''
  Operate on bulb; no gurantee of success.
  Input data 'params' must be a compiled into one string.
  E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
  '''
  if not bulb_idx2ip.has_key(idx):
    print "error: invalid bulb idx"
    return

  bulb_ip=bulb_idx2ip[idx]
  port=detected_bulbs[bulb_ip][5]
  try:
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    debug("connect "+ bulb_ip+ port ,"...")
    tcp_socket.connect((bulb_ip, int(port)))
    msg="{\"id\":" + str(next_cmd_id()) + ",\"method\":\""
    msg += method + "\",\"params\":[" + params + "]}\r\n"
    tcp_socket.send(msg)
    tcp_socket.close()
  except Exception as e:
    print "Unexpected error:", e

def toggle_bulb(idx):
  operate_on_bulb(idx, "toggle", "")

def set_bright(idx, bright):
  operate_on_bulb(idx, "set_bright", str(bright))

'''
Extension to Yeelight WifiBulb Lan controller provided by Yeelight (https://www.yeelight.com/en_US/developer)
author: gafurmp
'''
def set_BulbState(idx, state):
  '''
  Operate on bulb; no gurantee of success.
  Input data 'params' must be a compiled into one string.
  E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
  '''
  if not bulb_idx2ip.has_key(idx):
    print "error: invalid bulb idx"
    return

  bulb_ip=bulb_idx2ip[idx]
  port=detected_bulbs[bulb_ip][5]
  method="set_power"

  if state == "off":
    params="\"off\",\"smooth\",500"
  else:
    params="\"on\",\"smooth\",500"

  debug("Command Recieved:" + params)

  try:
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    debug("connect "+bulb_ip+ port +"...")
    tcp_socket.connect((bulb_ip, int(port)))
    msg="{\"id\":" + str(next_cmd_id()) + ",\"method\":\""
    msg += method + "\",\"params\":[" + params + "]}\r\n"
    tcp_socket.send(msg)
    tcp_socket.close()
  except Exception as e:
    print "Unexpected error:", e


def find_BulbState(idx):
  '''
  Operate on bulb; no gurantee of success.
  Input data 'params' must be a compiled into one string.
  E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
  '''
  if not bulb_idx2ip.has_key(idx):
    print "error: invalid bulb idx"
    return

  bulb_ip=bulb_idx2ip[idx]
  port=detected_bulbs[bulb_ip][5]
  method="get_prop"

  params="\"power\""

  debug("Command Recieved:" + params)

  try:
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    debug("connect "+bulb_ip+ port +"...")
    tcp_socket.connect((bulb_ip, int(port)))
    msg="{\"id\":" + str(next_cmd_id()) + ",\"method\":\""
    msg += method + "\",\"params\":[" + params + "]}\r\n"
    tcp_socket.send(msg)
    tcp_socket.close()
  except Exception as e:
    print "Unexpected error:", e

def recieve_BulbState():
  '''
  a standalone thread broadcasting search request and listening on all responses
  '''
  debug("bulbs_detection_loop running")
  search_interval=30000
  read_interval=100
  time_elapsed=0
  while True:
    if time_elapsed%search_interval == 0:
      send_search_broadcast()

    # scanner
    while True:
      try:
        ndata = scan_socket.recv(2048)
      except socket.error, e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            break
        else:
            print e
            sys.exit(1)
      handle_BulbResponse(ndata)
      sleep(0.02)
      break

    # passive listener
    while True:
      try:
        ndata, addr = listen_socket.recvfrom(2048)
      except socket.error, e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            break
        else:
            print e
            sys.exit(1)
      handle_BulbResponse(ndata)
      sleep(0.02)
      break

    time_elapsed+=read_interval
    sleep(read_interval/1000.0)

def handle_BulbResponse(ndata):
  '''
  Parse search response and extract all interested data.
  If new bulb is found, insert it into dictionary of managed bulbs. 
  '''
  global g_ylBulbStateAct
  location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
  match = location_re.search(ndata)
  if match == None:
    debug("invalid data received: " + ndata)
    return

  host_ip = match.group(1)
  if detected_bulbs.has_key(host_ip):
    bulb_id = detected_bulbs[host_ip][0]
  else:
    bulb_id = len(detected_bulbs)+1
  host_port = match.group(3)
  g_ylBulbStateAct = get_param_value(ndata, "power")
  debug("Bulb State: " + g_ylBulbStateAct)

def control_YeeLight():
  while True:
     run_YeeLightCtrl()
     sleep(0.02)

def run_YeeLightCtrl():
   debug("running Yeelight Controller....")
   global g_ylBulbStateAct
   global g_ylBulbStateReq
   currentTime = datetime.datetime.now()
   bulbStartTime = currentTime.replace(hour=18, minute=30, second=0, microsecond=0)
   bulbStopTime = currentTime.replace(hour=23, minute=55, second=0, microsecond=0)
   #debug("time now ="+ currentTime)

   target_BulbState = "off"
   if currentTime > bulbStartTime and currentTime < bulbStopTime:
      target_BulbState = "on"
   else:
      target_BulbState = "off"

   '''
   Add additional GPIO inputs, if you want to control the lamp with LDR or PIR inaddition and change the conditions accordingly
   '''

   if target_BulbState == "off":
      debug("Ausschalten... bulbState: "+ g_ylBulbStateAct)
      if g_ylBulbStateReq == "on" or g_ylBulbStateAct == "on":
           debug("Yeelight: TURN OFF")
           g_ylBulbStateReq = "off"
           set_BulbState(1, "off")
   else:
      debug("Einschalten... bulbState: "+ g_ylBulbStateAct)
      if g_ylBulbStateReq == "off" or g_ylBulbStateAct == "off":
           debug("Yeelight : TURN ON")
           g_ylBulbStateReq = "on"
           set_BulbState(1, "on")

'''
Main starts here
'''
print "Welcome to Yeelight WifiBulb Lan controller"
scan_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
fcntl.fcntl(scan_socket, fcntl.F_SETFL, os.O_NONBLOCK)
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_socket.bind(("", 1982))
fcntl.fcntl(listen_socket, fcntl.F_SETFL, os.O_NONBLOCK)
mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

detected_bulbs.clear()
bulb_idx2ip.clear()

'''
Start Bulb detection thread
'''
detection_thread = Thread(target=bulbs_detection_loop)
detection_thread.start()
sleep(0.2)

'''
Start BulbState detection thread
'''
bulbState_thread = Thread(target=recieve_BulbState)
bulbState_thread.start()
sleep(0.2)

'''
Start YeeLight controller thread
'''
ylCtrl_thread = Thread (target=control_YeeLight)
ylCtrl_thread.start()
sleep(0.02)

'''
End of execution... Join threads
'''
RUNNING = False
detection_thread.join()
bulbState_thread.join()
ylCtrl_thread.join()
#done
