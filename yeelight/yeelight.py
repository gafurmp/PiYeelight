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
from collections import OrderedDict


class YeeLight(object):
  """
  Yeelight class, which provides methods to control different aspects of yeelight smart bulb.
  """
  MCAST_GRP = '239.255.255.250'

  def __init__(self, debug='DISABLE'):
    self.scan_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    fcntl.fcntl(self.scan_socket, fcntl.F_SETFL, os.O_NONBLOCK)
    self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.listen_socket.bind(("", 1982))
    fcntl.fcntl(self.listen_socket, fcntl.F_SETFL, os.O_NONBLOCK)
    self.mreq = struct.pack("4sl", socket.inet_aton(self.MCAST_GRP), socket.INADDR_ANY)
    self.listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self.mreq)
    self.debug = debug
    self.current_command_id = 0
    self.detected_bulbs = {}
    self.bulb_idx2ip = {}

  def _debug(self, msg):
    if self.debug == 'ENABLE':
      print msg

  def _next_Cmd_Id(self):
    self.current_command_id += 1
    return self.current_command_id

  def send_Search_Broadcast(self):
    '''
    multicast search request to all hosts in LAN, do not wait for response
    '''
    multicase_address = (self.MCAST_GRP, 1982) 
    msg = "M-SEARCH * HTTP/1.1\r\n" 
    msg = msg + "HOST: 239.255.255.250:1982\r\n"
    msg = msg + "MAN: \"ssdp:discover\"\r\n"
    msg = msg + "ST: wifi_bulb"
    self.scan_socket.sendto(msg, multicase_address)
    self._debug("send search request: " + msg)

  def scan_Broadcast_Response(self):
    '''
    Scans socket for on all responses
    '''
    self._debug("scanning for response...")
    data = ''
    try:
      data = self.scan_socket.recv(2048)
    except socket.error as e:
      err = e.args[0]
      if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
        self._debug("Socker Error: {0}".format(e))
        return False
      else:
        self._debug("Socker Error: {0}".format(e))
        return False
    finally:
      if data is not '':
        self._debug("response recieved: " + data)
        self._handle_Search_Response(data)
        return True
      else:
        self._debug("no response...")
        return False

  def listen_Socket_Passive(self):
    '''
    Listens on socket for responses.
    Must be called in specified intervels for response after a request
    '''
    self._debug("listening for response...")
    data = ''
    try:
      data, addr = self.listen_socket.recvfrom(2048)
    except socket.error as e:
      err = e.args[0]
      if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
        self._debug("Socker Error: {0}".format(e))
        return False
      else:
        self._debug("Socker Error: {0}".format(e))
        return False
    finally:
      if data is not '':
        self._debug("response recieved: " + data)
        self._handle_Search_Response(data)
        return True
      else:
        self._debug("no response...")
        return False

  def _get_Param_Value(self, data, param):
    '''
    match line of 'param = value'
    '''
    param_re = re.compile(param+":\s*([ -~]*)") #match all printable characters
    match = param_re.search(data)
    value=""
    if match != None:
      value = match.group(1)
    return value

  def _handle_Search_Response(self, data):
    '''
    Parse search response and extract all interested data.
    If new bulb is found, insert it into dictionary of managed bulbs. 
    '''
    location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
    match = location_re.search(data)
    if match == None:
      self._debug( "invalid data received: " + data )
      return

    host_ip = match.group(1)
    if self.detected_bulbs.has_key(host_ip):
      bulb_id = self.detected_bulbs[host_ip][0]
    else:
      bulb_id = len(self.detected_bulbs)+1
    host_port = match.group(3)
    model = self._get_Param_Value(data, "model")
    power = self._get_Param_Value(data, "power")
    bright = self._get_Param_Value(data, "bright")
    rgb = self._get_Param_Value(data, "rgb")
    # use two dictionaries to store index->ip and ip->bulb map
    self.detected_bulbs[host_ip] = [bulb_id, model, power, bright, rgb, host_port]
    self.bulb_idx2ip[bulb_id] = host_ip
    self._display_Bulb(bulb_id)

  def _display_Bulb(self, idx):
    '''
    Display a bulb propertes
    idx: index of bulb
    '''
    if not self.bulb_idx2ip.has_key(idx):
      debug("error: invalid bulb idx")
      return
    bulb_ip = self.bulb_idx2ip[idx]
    model = self.detected_bulbs[bulb_ip][1]
    power = self.detected_bulbs[bulb_ip][2]
    bright = self.detected_bulbs[bulb_ip][3]
    rgb = self.detected_bulbs[bulb_ip][4]
    self._debug( str(idx) + ": ip=" \
      +bulb_ip + ",model=" + model \
      +",power=" + power + ",bright=" \
      + bright + ",rgb=" + rgb)

  def display_Bulbs(self):
    '''
    Displays all detected bulbs
    '''
    self._debug(str(len(self.detected_bulbs)) + " managed bulbs")
    for i in range(1, len(self.detected_bulbs)+1):
      self._display_Bulb(i)

  def _operate_On_Bulb(self, idx, method, params):
    '''
    Operate on bulb; no gurantee of success.
    Input data 'params' must be a compiled into one string.
    E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
    '''
    if not self.bulb_idx2ip.has_key(idx):
      self._debug("Error: invalid bulb idx")
      return

    bulb_ip=self.bulb_idx2ip[idx]
    port=self.detected_bulbs[bulb_ip][5]
    try:
      tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self._debug("connect "+ bulb_ip+ port +"...")
      tcp_socket.connect((bulb_ip, int(port)))
      msg="{\"id\":" + str(self._next_Cmd_Id()) + ",\"method\":\""
      msg += method + "\",\"params\":[" + params + "]}\r\n"
      tcp_socket.send(msg)
      tcp_socket.close()
    except Exception as e:
      self._debug("Unexpected error: {0}".format(e))

  def toggle_BulbState(self, idx):
    '''
    Toggles bulb's power
    idx: index of bulb
    '''
    self._operate_On_Bulb(idx, "toggle", "")

  def set_Brightness(self, idx, bright):
    '''
    Sets bulb's brightness
    idx: index of bulb
    bright: brightness in percentage
    '''
    self._operate_On_Bulb(idx, "set_bright", str(bright))

  def set_BulbPower(self, idx, power):
    '''
    Sets bulb's power
    idx: index of bulb
    power: on/ off
    '''
    method="set_power"
    if power == "off":
      params="\"off\",\"smooth\",500"
    else:
      params="\"on\",\"smooth\",500"
    self._operate_On_Bulb(idx, method, params)

  def request_BulbState(self, idx):
    '''
    Requests (broadcasted) bulb properties color, model, brightness and power.
    Caller must scan/ listen for the responses after the request.
    '''
    method="get_prop"
    params="\"power\",\"bright\",\"rgb\",\"model\""
    self._operate_On_Bulb(idx, method, params)

  def get_BulbPower(self, idx):
    '''
    Gets bulb's power
    idx: index of bulb
    '''
    bulb_ip = self.bulb_idx2ip[idx]
    power =  self.detected_bulbs[bulb_ip][2]
    self._debug(power)
    return power

  def get_BulbModel(self, idx):
    '''
    Gets bulb's model
    idx. index of bulb
    '''
    bulb_ip = self.bulb_idx2ip[idx]
    model =  self.detected_bulbs[bulb_ip][1]
    self._debug(model)
    return model

  def get_BulbBrightness(self, idx):
    '''
    Gets bulb's brightness
    idx: index of bulb
    '''
    bulb_ip = self.bulb_idx2ip[idx]
    bright =  self.detected_bulbs[bulb_ip][3]
    self._debug(bright)
    return bright

  def get_BulbColor(self, idx):
    '''
    Gets bulb's color
    idx: bulb index
    '''
    bulb_ip = self.bulb_idx2ip[idx]
    color =  self.detected_bulbs[bulb_ip][4]
    self._debug(color)
    return color

  def reset_Detected_Bulbs(self):
    '''
    Clears all detected bulbs and its indices.
    '''
    self.detected_bulbs.clear()
    self.bulb_idx2ip.clear()

  def is_Bulbs_Detected(self):
    '''
    Returns true if atleast one bulb is detected
    '''
    res = bool(self.bulb_idx2ip) 
    return res

  def set_BulbColor(self, idx, color = '1700', effect = 'smooth'):
    '''
    Sets bulb's color
    idx: bulb index
    color: range is 1700 ~ 6500
    effect: smooth/ sudden
    '''
    method="set_ct_abx"
    params=color + ",\" + effect + "\",500"
    self._operate_On_Bulb(idx, method, params)
