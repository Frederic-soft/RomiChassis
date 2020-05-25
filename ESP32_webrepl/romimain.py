############
# romimain.py for Micropython on ESP32
#
# Web REPL server for driving a Pololu Romi Chassis
# equipped with the Motor driver and power distribution board.
#
# See https://www.pololu.com/category/202/romi-chassis-and-accessories
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-10 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############
import webrepl
import sys
from machine import Pin
from romiesp32 import RomiPlatform

## TTGO T7_V1.4 board
# pinmap = {
# 	'lpwm': 25,
# 	'ldir': 32,
# 	'lslp': 4,
# 	'leca': 2,
# 	'lecb': 0,
# 	'rpwm': 19,
# 	'rdir': 18,
# 	'rslp': 26,
# 	'reca': 5,
# 	'recb': 23,
# 	'ctrl': 27
# }
# led = Pin(2, Pin.OUT)

## Cheap ESP32 WROOM-32 board with no spi RAM
pinmap = {
	'lpwm': 13,
	'ldir': 12,
	'lslp': 14,
	'leca': 26,
	'lecb': 27,
	'rpwm': 25,
	'rdir': 33,
	'rslp': 32,
	'reca': 34,
	'recb': 35,
	'ctrl': 15
}

# The builtin LED is on pin 2 on this board
led = Pin(2, Pin.OUT)

# Create the driver for the chassis
romp = RomiPlatform(pinmap)

# Get the right and left motors
rm = romp.rightmotor
lm = romp.leftmotor

"""
Send the status of the chassis to the connected client
"""
def sendStatus() :
  sys.stdout.write("UPDATE %d %d %f %d %f\n" %
                                   (led.value(),
                                       lm.count_a,
                                          lm.get_rpms(),
                                             rm.count_a,
                                                rm.get_rpms()
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
  elif args[0] == "MOVE" :
    romp.move(float(args[1]), float(args[2]))
  elif args[0] == "CRUISE" :
    romp.cruise(float(args[1]), float(args[2]))
  elif args[0] == "STOP" :
    romp.stop()
  elif args[0] == "SHUTDOWN" :
    romp.shutdown()
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
