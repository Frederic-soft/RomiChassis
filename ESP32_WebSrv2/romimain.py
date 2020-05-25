############
# romimain.py for Micropython on ESP32
#
# HTTP/WebSocket server using MicroWebSrv2 for driving a Pololu Romi Chassis
# equipped with the Motor driver and power distribution board.
#
# See https://github.com/jczic/MicroWebSrv2
# See https://www.pololu.com/category/202/romi-chassis-and-accessories
#
# This does not seem to work on a regular ESP32 (April 2020)
# When the web serveur runs, the timers and the IRQ in romiesp32 do not work
# It works on an ESP32 with spi RAM (WROVER-B)
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-10 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############

from MicroWebSrv2 import MicroWebSrv2
from machine import Pin
from romiesp32 import RomiPlatform

# Builtin LED is on pin 5 on this board
led = Pin(5, Pin.OUT)

# romp = RomiPlatform({
#     'lpwm': 13,
#     'ldir': 12,
#     'lslp': 14,
#     'leca': 26,
#     'lecb': 27,
#     'rpwm': 25,
#     'rdir': 33,
#     'rslp': 32,
#     'reca': 34,
#     'recb': 35,
#     'ctrl': 15
#   })

## TTGO T7_V1.4 board
romp = RomiPlatform({
    'lpwm': 25,
    'ldir': 32,
    'lslp': 4,
    'leca': 2,
    'lecb': 0,
    'rpwm': 19,
    'rdir': 18,
    'rslp': 26,
    'reca': 5,
    'recb': 23,
    'ctrl': 27
  })
rm = romp.rightmotor
lm = romp.leftmotor

"""
Send the status of the chassis to the client
"""
def sendStatus(webSocket) :
  webSocket.SendTextMessage("UPDATE %d %d %f %d %f" %
                                   (led.value(),
                                       lm.count_a,
                                          lm.get_rpms(),
                                             rm.count_a,
                                                rm.get_rpms()
                            ))

"""
Accept connections to the web socket server
"""
def _acceptWebSocketCallback(webSrv, webSocket) :
  print("WS ACCEPT")
  webSocket.OnTextMessage   = _recvTextCallback
  webSocket.OnBinaryMessage = _recvBinaryCallback
  webSocket.OnClosed        = _closedCallback

"""
Handle text messages received on the web socket
"""
def _recvTextCallback(webSocket, msg) :
  print("WS RECV TEXT : %s" % msg)
  args = msg.split()
  if args[0] == "LED_ON" :
    led.on()
  elif args[0] == "LED_OFF" :
    led.off()
  elif args[0] == "STAT" :
    sendStatus(webSocket)
  elif args[0] == "MOVE" :
    romp.move(float(args[1]), float(args[2]))
  elif args[0] == "CRUISE" :
    romp.cruise(float(args[1]), float(args[2]))
  elif args[0] == "STOP" :
    romp.stop()
  elif args[0] == "SHUTDOWN" :
    romp.shutdown()
  else :
    webSocket.SendTextMessage("Unknow command %s" % msg)

"""
Handle binary data received on the web socket (do nothing)
"""
def _recvBinaryCallback(webSocket, data) :
  print("WS RECV DATA : %s" % data)

"""
Handle the ending of the connection by shutting down the power on the chassis
"""
def _closedCallback(webSocket) :
  print("WS CLOSED")
  romp.shutdown()


# Load the web socket module (this fails without spi RAM)
wsMod = MicroWebSrv2.LoadModule('WebSockets')
wsMod.OnWebSocketAccepted = _acceptWebSocketCallback
# Create the server
srv = MicroWebSrv2()
# Select a lightweight configuration
srv.SetEmbeddedConfig()
# Start the server
srv.StartManaged()
