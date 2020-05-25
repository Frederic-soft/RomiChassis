############
# romimain.py for Micropython on ESP32
#
# This module is a web interface to another board controlling a Romi chassis
# equipped with the Motor driver and power distribution board.
#
# See https://www.pololu.com/category/202/romi-chassis-and-accessories
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-02 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############
# You will need MicroWebSrv: https://github.com/jczic/MicroWebSrv
from microWebSrv import MicroWebSrv
from machine import UART

# UART(0) is the REPL (the one connected to the USB port?)
# UART(1) is on TX0/RX0 (10/9) and seems to be linked to the REPL too
# UART(2) is on TX2/RX2 (17/16)
uart=UART(2, baudrate=115200, timeout=1000)

"""
Send the status of the chassis to the client.
We first ask for the status of the chassis to the other board through the serial link.
Then we send the answer of the board to the client.
"""
def sendStatus(webSocket) :
  uart.write("STAT\r\n".encode()) # Ask for an update of the status of the Romi
  buf = uart.readline()           # Read the answer (timeout is 1s)
  if buf is None :                # No answer
    webSocket.SendText("NOK")     # Send error to the web server
  else :
    webSocket.SendText(buf.decode()) # Send answer to the web server

"""
Accept a connection to the web socket.
"""
def _acceptWebSocketCallback(webSocket, httpClient) :
  print("WS ACCEPT")
  webSocket.RecvTextCallback   = _recvTextCallback
  webSocket.RecvBinaryCallback = _recvBinaryCallback
  webSocket.ClosedCallback   = _closedCallback

"""
Handle a text message, by transferring it on the serial link to the other board.
"""
def _recvTextCallback(webSocket, msg) :
  uart.write((msg+'\r\n').encode())
  buf = uart.readline()
  if buf is None :                # No answer
    webSocket.SendText("NOK")     # Send error to the web server
  else :
    webSocket.SendText(buf.decode()) # Send answer to the web server

"""
Handle binary messages (don't do anything)
"""
def _recvBinaryCallback(webSocket, data) :
  print("WS RECV DATA : %s" % data)

"""
Handle the ending of the connection.
"""
def _closedCallback(webSocket) :
  print("WS CLOSED")
  uart.write(('CLOSE\r\n').encode())

# Create the HTTP server
srv = MicroWebSrv(webPath='www/')
srv.MaxWebSocketRecvLen     = 256
srv.WebSocketThreaded   = False
# Install the callback for web socket connections
srv.AcceptWebSocketCallback = _acceptWebSocketCallback
# Start the server
srv.Start()
