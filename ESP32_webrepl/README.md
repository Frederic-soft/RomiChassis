Version using MicroPython web REPL on an ESP32
================================
You may need:
* my [boot_network](https://github.com/Frederic-soft/ESP32/tree/master/boot_network) code for setting up the WiFi.

If you are only interested in the client/server aspect, you can import ledmain instead of romimain and type `ledmain.start()` to control the builtin LED from a web browser displaying the index.html page.