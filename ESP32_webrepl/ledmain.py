############
# romimain.py for Micropython on ESP32
#
# Web REPL server for controlling the builtin LED of an ESP32
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-10 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############
import webrepl
import sys
from machine import Pin

# The builtin LED is on pin 2 on this board
led = Pin(2, Pin.OUT)

"""
Send the status of the LED
"""
def sendStatus() :
  sys.stdout.write("UPDATE %d %d %f %d %f\n" %
                                   (led.value(),
                                       0,
                                          0,
                                             0,
                                                0
                            ))

"""
Process a command received from the client
"""
def processCommand(msg) :
  print("WS RECV : %s" % msg)
  args = msg.split()
  if args[0] == "LED_ON" :
    led.on()
  elif args[0] == "LED_OFF" :
    led.off()
  elif args[0] == "STAT" :
    sendStatus()
  else :
    print("Unknown command %s" % msg)

"""
Start the web REPL and execute an infinite loop to process the requests of the client
"""
def start() :
  webrepl.start(port=8080, password='')
  while True :
    l = sys.stdin.readline().strip()
    if l != "" :
      processCommand(l)

"""
Stop the web REPL.
"""
def stop() :
  webrepl.stop()
