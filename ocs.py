#!/usr/bin/env python3
# oozeBot Control Service v1.0
# Release Date: 3/14/2022

from asyncio.base_subprocess import ReadSubprocessPipeProto
import time

SSID = ""
PWORD = ""
CNTRY = "US"

from dsf.commands.basecommands import MessageType
from dsf.commands.basecommands import LogLevel
from dsf.commands.code import CodeType
from dsf.connections import CommandConnection, InterceptConnection, SubscribeConnection
from dsf.initmessages.clientinitmessages import InterceptionMode, SubscriptionMode

###################################################################################################

def run(command:str):
  from subprocess import Popen, PIPE, STDOUT
  from io import StringIO
  popen = Popen(command, stdout=PIPE, stderr=STDOUT, universal_newlines=True, shell=True)
  out = StringIO()
  for line in popen.stdout:
    out.write(line)
    popen.stdout.close()
    return_code = popen.wait()
    if not return_code == 0:
      raise RuntimeError('The process call "{}" returned with code {}. The return code is not 0, thus an error occurred.'.format(list(command), return_code))
    stdout_string = out.getvalue()
    out.close()
    return stdout_string

###################################################################################################

def LogMsg(message:str, type:str):
  command_connection = CommandConnection()
  command_connection.connect()
  if type == "error":
    command_connection.write_message(MessageType.Error, message, True, LogLevel.Info)
  elif type == "warning":
    command_connection.write_message(MessageType.Warning, message, True, LogLevel.Info)
  elif type == "success":
    command_connection.write_message(MessageType.Success, message, True, LogLevel.Info)
  command_connection.close()

###################################################################################################

def ParseParam(value:str, stripQuotes:bool=False):
  value = str(value)
  if value == "None":
    return ""
  else:
    value = value[2:]
    value = value[:len(value)-1]
    if stripQuotes:
      value = value.strip('"')
    return value

###################################################################################################

if __name__ == "__main__":
  filters = ("M587", "M9020", "M9988", "M9999")
  intercept_connection = InterceptConnection(InterceptionMode.PRE, filters=filters)
  intercept_connection.connect()
  while True:
    cde = intercept_connection.receive_code()

    if cde.type == CodeType.MCode:
      ###############################################################
      # M587 - Networking
      ###############################################################
      if cde.majorNumber == 587:
        tVar = ParseParam(cde.parameter("H"))
        intercept_connection.resolve_code()
        if len(tVar) > 0: # Update hostname
          with open("/etc/hostname", "w") as fil:
            fil.writelines([ \
              tVar \
            ])
            fil.close()
          with open("/etc/hosts", "w") as fil:
            fil.writelines([ \
              "127.0.0.1       localhost\n", \
              "::1             localhost ip6-localhost ip6-loopback\n", \
              "ff02::1         ip6-allnodes\n", \
              "ff02::2         ip6-allrouters\n", \
              "\n", \
              "127.0.1.1       " + tVar + "\n" \
            ])
            fil.close()
          LogMsg("RPi hostname set to: " + tVar, "success")
          LogMsg("RPi is rebooting - ignore connection warnings", "warning")
          time.sleep(2)
          run("sudo reboot")
        tVar = ParseParam(cde.parameter("C"))
        if len(tVar) > 0:
          CNTRY = tVar
        tVar = ParseParam(cde.parameter("S"))
        if len(tVar) > 0:
          SSID = tVar
        tVar = ParseParam(cde.parameter("P"))
        if len(tVar) > 0:
          PWORD = tVar
        intercept_connection.resolve_code()
        if len(SSID) > 0 and len(PWORD) > 0: # Update WiFi
          with open("/boot/wpa_supplicant.conf", "w") as fil:
            fil.writelines([ \
              "country=" + CNTRY + "\n", \
              "update_config=1\n", \
              "ctrl_interface=/var/run/wpa_supplicant\n", \
              "network={\n", \
              "        ssid=\"" + SSID + "\"\n", \
              "        psk=\"" + PWORD + "\"\n", \
              "}" \
            ])
            fil.close()
          LogMsg("RPi is rebooting - ignore connection warnings", "warning")
          time.sleep(2)
          run("sudo reboot")

      ###############################################################
      # M9020 - Restart webCam service
      ###############################################################
      elif cde.majorNumber == 9020:
        Action = ParseParam(cde.parameter("A")).upper()
        intercept_connection.resolve_code()
        if Action == "RESTART":
          run("sudo systemctl stop hawkeye.service")
          run("sudo systemctl start hawkeye.service")
          LogMsg("Webcam service restarted.", "success")
        elif Action == "ENABLE":
          run("sudo systemctl enable hawkeye.service")
          run("sudo systemctl start hawkeye.service")
          LogMsg("Webcam service enabled.", "success")
        elif Action == "DISABLE":
          run("sudo systemctl stop hawkeye.service")
          run("sudo systemctl disable hawkeye.service")
          LogMsg("Webcam service disabled.", "success")
        else:
          LogMsg("Invalid parameter passed to M9020 - expected A\"Restart\", A\"Enable\", or A\"Disable\"", "error")

      ###############################################################
      # M9988 - Switch between release / beta channel
      ###############################################################
      elif cde.majorNumber == 9988:
        tVar = ParseParam(cde.parameter("C")).upper()
        intercept_connection.resolve_code()
        if tVar == "RELEASE":
          with open("/etc/apt/sources.list.d/duet3d.list", "w") as fil:
            fil.writelines([ \
              "deb https://pkg.duet3d.com/ stable armv7", \
            ])
            fil.close()
          LogMsg("Release channel selected", "success")
        elif tVar == "BETA":
          with open("/etc/apt/sources.list.d/duet3d.list", "w") as fil:
            fil.writelines([ \
              "deb https://pkg.duet3d.com/ unstable armv7", \
            ])
            fil.close()
          LogMsg("Beta channel selected", "success")
        elif tVar == "NONE":
          with open("/etc/apt/sources.list.d/duet3d.list", "w") as fil:
            fil.writelines([ \
              "", \
            ])
            fil.close()
          LogMsg("No channel selected", "success")
        else:
          LogMsg("Invalid parameter passed to M9988 - expected C\"Release\" or C\"Beta\"", "error")

      ###############################################################
      # M9999 - Reboot / Shutdown RPi
      ###############################################################
      elif cde.majorNumber == 9999:
        Action = ParseParam(cde.parameter("A")).upper()
        intercept_connection.resolve_code()
        if Action == "REBOOT":
          LogMsg("RPi is rebooting - ignore connection warnings", "warning")
          time.sleep(2)
          run("sudo reboot")
        elif Action == "SHUTDOWN":
          LogMsg("RPi is shutting down - ignore connection warnings", "warning")
          time.sleep(2)
          run("sudo shutdown -h 0")
        else:
          LogMsg("Invalid parameter passed to M9999 - expected A\"Reboot\" or A\"Shutdown\"", "error")