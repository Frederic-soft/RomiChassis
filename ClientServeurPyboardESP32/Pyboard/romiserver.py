############
# romiserver.py for Micropython on Pyboard
#
# This module is a reads command on the UART of the Pyboard to drive a Romi chassis.
# The commands are sent on the serial link by an ESP32 which runs an HTTP and a 
# WebSocket server to receive commands from the user.
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-02 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############
from pyb import UART, Pin, LED
from romipyb import RomiPlatform

# UART(1) is on TX=X9/RX=X10
uart = UART(1, baudrate=115200, timeout=1000)
led = LED(4)  # the blue LED

romp = RomiPlatform()
lm = romp.leftmotor
rm = romp.rightmotor

def sendStatus() :
  status = "UPDATE %d %d %f %d %f\r\n" % \
                            (led.intensity(),
                                lm.count_a,
                                   lm.get_rpms(),
                                      rm.count_a,
                                         rm.get_rpms()
                            )
  uart.write(status.encode())

# Read commands and drive the chassis
while True :
  buf = uart.readline()    # Read next command with a timeout of 1s
  if buf is None :
    continue
  args = buf.decode().split()
#  print(args)
  
  if args[0] == "LED_ON" :
    led.on()
    uart.write("OK\r\n".encode())
  elif args[0] == "LED_OFF" :
    led.off()
    uart.write("OK\r\n".encode())
  elif args[0] == "STAT" :
    sendStatus()
  elif args[0] == "MOVE" :
    romp.move(float(args[1]), float(args[2]))
    uart.write("OK\r\n".encode())
  elif args[0] == "CRUISE" :
    romp.cruise(float(args[1]), float(args[2]))
    uart.write("OK\r\n".encode())
  elif args[0] == "STOP" :
    romp.stop()
    uart.write("OK\r\n".encode())
  elif args[0] == "SHUTDOWN" :
    romp.shutdown()
    uart.write("OK\r\n".encode())
  else :
    uart.write(("ERR Unknow command %s\r\n" % args[0]).encode())
