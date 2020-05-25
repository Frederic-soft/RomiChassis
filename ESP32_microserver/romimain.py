############
# romimain.py for Micropython on ESP32
#
# HTTP/WebSocket server for driving a Pololu Romi Chassis
# equipped with the Motor driver and power distribution board.
#
# See https://www.pololu.com/category/202/romi-chassis-and-accessories
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-10 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############
# httpserver and wsserver are from https://github.com/Frederic-soft/ESP32/tree/master/microserver
from httpserver import HttpServer
from wsserver import WebSocketServer

from machine import Pin
from romiesp32 import RomiPlatform

"""
A subclass of WebSocketServer that implements a protocol to control 
the romi platform on an ESP32
"""
class RomiServer (WebSocketServer) :
  """
  Initialize the server to listen on port 8080 (the 80 port is used by the HTTP server)
  The default address mask allows connections from anywhere. Use 127.0.0.1 if
  you want to restrict connection to the local host.
  'romi' is the RomiPlatform to control.
  'password' is the password that will be required by the webrepl stuff to connect to the websocket.
  'ledpin' is the number of the pin for the builtin LED.
  If 'debug' is True, a transcript of the communications with the clients will be printed
  in the console.
  """
  def __init__(self, romi, port=8080, address="0.0.0.0", password='', ledpin=2, debug=False) :
    super().__init__(port, address, password)
    self._debug = debug
    self._led = Pin(ledpin, Pin.OUT)
    self._romi = romi
    self._led.on()
  
  """
  Process requests from the client:
    - LED_ON requests to switch the builtin LED on
    - LED_OFF requests to switch the builtin LED off
    - STAT requests to send the status of the platform
  The only possible answer is "UPDATE L CL RL CR RR", where:
    - L is the status of the LED
    - CL is the count of the right wheel encoder
    - RL is the RPM of the right wheel
    - CR is the count of the left wheel encoder
    - RR is the RPM of the left wheel
  """
  def process_request(self, message) :
    if self._debug :
      print("# RECEIVED " + str(message))
    if message is None :   # Close server
      return None
    message = message.split()
    if len(message) == 0 :
      pass
    elif message[0] == "LED_ON" :
      self._led.on()
    elif message[0] == "LED_OFF" :
      self._led.off()
    elif message[0] == "STAT" :
      pass
    elif message[0] == "MOVE" :
      self._romi.move(float(message[1]), float(message[2]))
    elif message[0] == "CRUISE" :
      self._romi.cruise(float(message[1]), float(message[2]))
    elif message[0] == "LTHROT" :
      self._romi.throttle(int(message[1]), None)
    elif message[0] == "RTHROT" :
      self._romi.throttle(None, int(message[1]))
    elif message[0] == "STOP" :
      self._romi.stop()
    elif message[0] == "SHUTDOWN" :
      self._romi.shutdown()
    else :
      if self._debug :
        print("# UNKNOWN REQUEST: " + message)
    return ("UPDATE %d %d %f %d %f %d %d\n" %
                   (self._led.value(),
                       self._romi.leftmotor.count_a,
                          self._romi.leftmotor.get_rpms(),
                             self._romi.rightmotor.count_a,
                                self._romi.rightmotor.get_rpms(),
                                   self._romi.leftmotor.getThrottle(),
                                      self._romi.rightmotor.getThrottle()
           ))
  
  """
  Redefined method to install process_request as the request handler
  """
  def do_accept(self, address) :
    h = super().do_accept(address)  # Reuse the superclass behavior
    if h is None :
      if self._debug :
        print("# Rejecting connection from: ", address)
    else :            # if the connection is accepted
      if self._debug :
        print("# Accepting connection from: ", address)
      self._led.off()
      return self.process_request   #   return our request handler
  
  """
  Redefined method to print a message when a connection is closed
  """
  def close_handler(self, wsreader) :
    if self._debug :
      print("# Closing connection from", self.getClientFromReader(wsreader)[0])
    self._led.on()
    super().close_handler(wsreader)  # Reuse superclass behavior to really close the connection

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
led = Pin(2, Pin.OUT)

romp = RomiPlatform(pinmap)

# A suitable index.html file should be put in /www on the ESP32 internal storage
hsrv = HttpServer()                            # Create the HTTP server on port 80
wsrv = RomiServer(romp, 8080, debug=False)     # Create the web socket server on port 8080
print("Point your browser at:", hsrv.start())  # Start the HTTP server
print("Web socket URL:", wsrv.start())         # Start the web socket server
