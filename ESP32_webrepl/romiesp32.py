############
# romiesp32.py for Micropython on ESP32
#
# This module is a driver for the Romi chassis by Pololu, 
# equipped with the Motor driver and power distribution board.
#
# See https://www.pololu.com/category/202/romi-chassis-and-accessories
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-10 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############
from machine import Pin, PWM, Timer
import time

"""
This class is for driver one motor of the chassis and its rotation encoder
"""
class RomiMotor :
  """
  We reuse the same timer for all instances of the class, so this is the callback
  of the class, which calls the handlers in each instance.
  """
  @classmethod
  def class_rpm_handler(cls, tim) :
    for h in cls.rpm_handlers :
      h(tim)
  
  # List of the rpm handlers of the instances, necessary because we share a single timer.
  rpm_handlers = []
  # The shared timer
  rpmtimer = None
  
  """
  Initialize a RomiMotor, with pwm, dir, sleep, enca and enb as the pin numbers for 
  respectively the PWM, the direction control, the sleep control of the motor, 
  and the A and B outputs of the rotation encoder.
  """
  def __init__(self, pwm, dir, sleep, enca, encb) :
    self.pwm = PWM(Pin(pwm, Pin.OUT))
    self.pwm.duty(0)
    self.dir = Pin(dir, Pin.OUT)
    self.dir.off()          # O = forward, 1 = reverse
    self.sleep = Pin(sleep, Pin.OUT)
    self.sleep.off()        # 0 = sleep, 1 = active
    self.enca = Pin(enca, Pin.IN, Pin.PULL_UP)
    self.encb = Pin(encb, Pin.IN, Pin.PULL_UP)
    self.count_a = 0    # counter for impulses on the A output of the encoder
    self.target_a = 0   # target value for the A counter (for controlled rotation)
    self.count_b = 0    # counter for impulses on the A output of the encoder
    self.time_a = 0     # last time we got an impulse on the A output of the encoder
    self.time_a2 = 0    # current time of an A impulse (should be local to the enca_handler)
    self.time_b = 0     # last time we got an impulse on the B output of the encoder
    self.dirsensed = 0  # direction sensed through the phase of the A and B outputs
    self.rpm = 0        # current speed in rotations per second
    self.rpm_last_a = 0 # value of the A counter when we last computed the rpms
    self.cruise_rpm = 0 # target value for the rpms
    self.enca.irq(trigger=Pin.IRQ_RISING, handler=self.enca_handler)
    self.encb.irq(trigger=Pin.IRQ_RISING, handler=self.encb_handler)
    if RomiMotor.rpmtimer is None : # create only one shared timer for all instances
      RomiMotor.rpmtimer = Timer(-1)
      RomiMotor.rpmtimer.init(period=250, mode=Timer.PERIODIC,
                              callback=RomiMotor.class_rpm_handler)
    RomiMotor.rpm_handlers.append(self.rpm_handler) # register the handler for this instance
  
  """
  Handler for interrupts caused by impulses on the A output of the encoder.
  This is where we sense the rotation direction and adjust the throttle to 
  reach a target number of rotations of the wheel.
  """
  def enca_handler(self, pin) :
    self.count_a += 1
    self.time_a2 = time.ticks_ms()
    if time.ticks_diff(self.time_a2, self.time_b) > time.ticks_diff(self.time_b, self.time_a) :
      self.dirsensed = -1   # A occurs before B
    else :
      self.dirsensed = 1    # B occurs before A
    self.time_a = self.time_a2
    if self.target_a > 0 :  # If we have a target rotation
      if self.count_a >= self.target_a :
        self.pwm.duty(0)    # If we reached of exceeded the rotation, stop the motor
        self.target_a = 0   # remove the target
      elif (self.target_a - self.count_a) < 30 :
        self.pwm.duty(70)   # If we are very close to the target, slow down a lot
      elif (self.target_a - self.count_a) < 60 :
        self.pwm.duty(150)  # If we are close to the target, slow down

  """
  Handler for interrupts caused by impulses on the B output of the encoder.
  """
  def encb_handler(self, pin) :
    self.count_b += 1
    self.time_b = time.ticks_ms() # Memorize the time of the impulse to compute the phase

  """
  This is the handler of the timer interrupts to compute the rpms
  """
  def rpm_handler(self, tim) :
    self.rpm = 4 * (self.count_a - self.rpm_last_a) # The timer is at 4Hz
    self.rpm_last_a = self.count_a  # Memorize the number of impulses on A
    if self.cruise_rpm != 0 :       # If we have an RPM target
      # Add a correction to the PWM according to the difference in RPMs
      delta = abs(self.rpm - self.cruise_rpm)
      if delta < 100 :
        corr = delta // 4
      elif delta < 500 :
        corr = delta // 2
      else :
        corr = delta
      if self.cruise_rpm < self.rpm :
        self.pwm.duty(max(50, self.pwm.duty() - corr))
      else :
        self.pwm.duty(min(1023, self.pwm.duty() + corr))
  
  """
  Set the power of the motor in percents.
  Positive values go forward, negative values go backward.
  """
  def throttle(self, pct) :
    if pct is None :
      return
    if pct < 0 :
      self.dir.on()
      pct = -pct
    else :
      self.dir.off()
    self.pwm.duty((pct*1023)//100)
    self.sleep.on()
  
  """
  Get the current power as a percentage of the max power.
  The result is positive if the motor runs forward, negative if it runs backward.
  """
  def getThrottle(self) :
    thr = (self.pwm.duty() * 100) // 1023
    if self.dir.value() > 0 :
      thr = -thr
    return thr
  
  """
  Release the motor to let it rotate freely.
  """
  def release(self, release=True) :
    if release :
      self.sleep.off()
    else :
      self.sleep.on()
  
  """
  Perform 'turns' rotations of the wheel at 'power' percents of the max power.
  If 'turns' is positive, the wheel turns forward, if it is negative, it turns backward.
  """
  def rotatewheel(self, turns, power=20):
    if turns < 0 :
      sign = -1
      turns = -turns
    else :
      sign = 1
    self.count_a = 0
    self.count_b = 0
    self.target_a = int(360 * turns)
    self.throttle(sign*power)
  
  """
  Wait for the rotations requested by 'rotatewheel' to be done.
  """
  def wait(self) :
    while self.count_a < self.target_a :
      pass

  """
  Set a target RPMs. The wheel turns in its current rotation direction,
  'rpm' should be non negative.
  """
  def cruise(self, rpm) :
    self.cruise_rpm = int(rpm * 60)
  
  """
  Get the current RPMs. This is always non negative, regardless of the rotation direction.
  """
  def get_rpms(self) :
    return self.rpm / 60
  
  """
  Cancel all targets of rotation and RPM
  """
  def clear(self) :
    self.target_a = 0
    self.cruise_rpm = 0

  """
  Stop the motor.
  """
  def stop(self) :
    self.clear()
    self.throttle(0)

"""
A class for controlling a Pololu Romi chassis equipped with the Motor driver and 
power distribution board.
"""
class RomiPlatform :
  """
  The pinout of the chassis is given as a dictionnary. These are the default values
  that I find handy when using an Espressif dev kit with a WROOM-32 and 30 pins.
  """
  default_pins = {
    'lpwm': 13,   # left motor PWM
    'ldir': 12,   # left motor direction
    'lslp': 14,   # left motor sleep
    'leca': 26,   # left motor encoder A
    'lecb': 27,   # left motor encoder B
    'rpwm': 25,   # right motor PWM
    'rdir': 33,   # right motor direction
    'rslp': 32,   # right motor sleep
    'reca': 34,   # right motor encoder A
    'recb': 35,   # right motor encoder B
    'ctrl': 15    # CTRL pin to control the power switch of the chassis
  }
  
  """
  Create a controller for a chassis with the given pinout
  """
  def __init__(self, pins=default_pins) :
    self.leftmotor = RomiMotor(
      pins['lpwm'],pins['ldir'],pins['lslp'],pins['leca'],pins['lecb']
    )
    self.rightmotor = RomiMotor(
      pins['rpwm'],pins['rdir'],pins['rslp'],pins['reca'],pins['recb'],
    )
    self.control = Pin(pins['ctrl'], Pin.OPEN_DRAIN, value=1)

  """
  Set the throttle (power in percents) on the left and right motors.
  Positive power is forward, negative power is backward. Passing None keeps the 
  previous value for the power, so it is possible to change the power on only one motor.
  """
  def throttle(self, lpow, rpow) :
    self.leftmotor.throttle(lpow)
    self.rightmotor.throttle(rpow)
  
  """
  Get the power on the motors as a percentage of the maximum power.
  Positive power is forward, negative power is backward.
  """
  def getThrottle(self) :
    return (self.leftmotor.getThrottle(), self.rightmotor.getThrottle())

  """
  Make the wheels turn by a given number of turns, at 'power' percents of the 
  maximum power. 'lturns' and 'rturns' may be floats.
  Positive values turn forward, negative values turn backward.
  """
  def move(self, lturns, rturns, power=20) :
    self.leftmotor.rotatewheel(lturns, power)
    self.rightmotor.rotatewheel(rturns, power)
  
  """
  Set a target RPM value for the wheels.
  The current rotation direction is preserved, only  the rotation speed is regulated.
  """
  def cruise(self, lrpms, rrpms) :
    self.leftmotor.cruise(lrpms)
    self.rightmotor.cruise(rrpms)

  """
  Cancel all rotation and RPM targets.
  """
  def clear(self) :
    self.leftmotor.clear()
    self.rightmotor.clear()

  """
  Stop both motors.
  """
  def stop(self) :
    self.leftmotor.stop()
    self.rightmotor.stop()
  
  """
  Release both motors, let them turn freely.
  """
  def release(self, release=True) :
    self.leftmotor.release(release)
    self.rightmotor.release(release)
  
  """
  Shutdown the power on the chassis. This will also power down the ESP32 if 
  it is powered by the VCC MD pin of the chassis.
  """
  def shutdown(self) :
    # Drive the control pin low to shutdown the power of the platform
    self.control.off()

  """
  Power on the chassis.
  """
  def startup(self) :
    # Drive the control pin high to power the platform
    self.control.on()
