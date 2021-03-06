############
# romipyb.py for Micropython on Pyboard
#
# This module is a driver for the Romi chassis by Pololu, 
# equipped with the Motor driver and power distribution board.
#
# See https://www.pololu.com/category/202/romi-chassis-and-accessories
#
# © Frédéric Boulanger <frederic.softdev@gmail.com>
# 2020-04-02 -- 2020-05-24
# This software is licensed under the Eclipse Public License 2.0
############
import pyb
from pyb import Pin, Timer, ExtInt

import micropython
# The following line is useful to debug error in IRQ callbacks
#micropython.alloc_emergency_exception_buf(100)

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
  Initialize a RomiMotor, connected either to the 'X' side or the 'Y' side of the Pyboard.
  On either side (? is 'X' or 'Y'):
    - PWM is on pin ?1
    - DIR is on pin ?2
    - SLEEP is on pin ?3
    - ENCA is on pin ?4
    - ENCB is on pin ?5
  """
  def __init__(self, X=True) :
    if X :
      self.pwmpin = Pin('X1', Pin.OUT_PP)
      self.pwmtim = Timer(2, freq=5000)
      self.pwm = self.pwmtim.channel(1, mode=Timer.PWM, pin=self.pwmpin)
      self.pwm.pulse_width(0)
      self.dir = Pin('X2', Pin.OUT_PP)
      self.dir.off()          # O = forward, 1 = reverse
      self.sleep = Pin('X3', Pin.OUT_PP)
      self.sleep.value(0)        # 0 = sleep, 1 = active
      self.enca = Pin('X4', Pin.IN, Pin.PULL_UP)
      self.encb = Pin('X5', Pin.IN, Pin.PULL_UP)
    else :
      self.pwmpin = Pin('Y1', Pin.OUT_PP)
      self.pwmtim = Timer(8, freq=5000)
      self.pwm = self.pwmtim.channel(1, mode=Timer.PWM, pin=self.pwmpin)
      self.pwm.pulse_width(0)
      self.dir = Pin('Y2', Pin.OUT_PP)
      self.dir.off()          # O = forward, 1 = reverse
      self.sleep = Pin('Y3', Pin.OUT_PP)
      self.sleep.value(0)        # 0 = sleep, 1 = active
      self.enca = Pin('Y4', Pin.IN, Pin.PULL_UP)
      self.encb = Pin('Y5', Pin.IN, Pin.PULL_UP)
    self.pwmscale = (self.pwmtim.period() + 1) // 100 # scale factor for percent power
    self.count_a = 0      # counter for impulses on the A output of the encoder
    self.target_a = 0     # target value for the A counter (for controlled rotation)
    self.count_b = 0      # counter for impulses on the B output of the encoder
    self.time_a = 0       # last time we got an impulse on the A output of the encoder
    self.time_b = 0       # last time we got an impulse on the B output of the encoder
    self.elapsed_a_b = 0  # time elapsed between an impulse on A and an impulse on B
    self.dirsensed = 0    # direction sensed through the phase of the A and B outputs
    self.rpm = 0          # current speed in rotations per second
    self.rpm_last_a = 0   # value of the A counter when we last computed the rpms
    self.cruise_rpm = 0   # target value for the rpms
    ExtInt(self.enca, ExtInt.IRQ_RISING, Pin.PULL_UP, self.enca_handler)
    ExtInt(self.encb, ExtInt.IRQ_RISING, Pin.PULL_UP, self.encb_handler)
    if RomiMotor.rpmtimer is None :   # create only one shared timer for all instances
      RomiMotor.rpmtimer = Timer(4)
      RomiMotor.rpmtimer.init(freq=4, callback=RomiMotor.class_rpm_handler)
    RomiMotor.rpm_handlers.append(self.rpm_handler) # register the handler for this instance
  
  """
  Handler for interrupts caused by impulses on the A output of the encoder.
  This is where we sense the rotation direction and adjust the throttle to 
  reach a target number of rotations of the wheel.
  """
  def enca_handler(self, pin) :
    self.count_a += 1
    self.time_a = pyb.millis()
    if pyb.elapsed_millis(self.time_b) > self.elapsed_a_b :
      self.dirsensed = -1   # A occurs before B
    else :
      self.dirsensed = 1    # B occurs before A
    if self.target_a > 0 :  # If we have a target rotation
      if self.count_a >= self.target_a :
        self.pwm.pulse_width(0)   # If we reached of exceeded the rotation, stop the motor
        self.target_a = 0         # remove the target
      elif (self.target_a - self.count_a) < 30 :
        self.pwm.pulse_width(7 * self.pwmscale)   # If we are very close to the target, slow down a lot
      elif (self.target_a - self.count_a) < 60 :
        self.pwm.pulse_width(15 * self.pwmscale)  # If we are close to the target, slow down

  """
  Handler for interrupts caused by impulses on the B output of the encoder.
  """
  def encb_handler(self, pin) :
    self.count_b += 1
    self.elapsed_a_b = pyb.elapsed_millis(self.time_a)  # Memorize the duration since the last A impulse

  """
  This is the handler of the timer interrupts to compute the rpms
  """
  def rpm_handler(self, tim) :
    self.rpm = 4 * (self.count_a - self.rpm_last_a)   # The timer is at 4Hz
    self.rpm_last_a = self.count_a      # Memorize the number of impulses on A
    if self.cruise_rpm != 0 :           # If we have an RPM target
      # Add a correction to the PWM according to the difference in RPMs
      delta = abs(self.rpm - self.cruise_rpm)
      if delta < 100 :
        corr = delta // 40
      elif delta < 500 :
        corr = delta // 20
      else :
        corr = delta // 10
      if self.cruise_rpm < self.rpm :
      	self.pwm.pulse_width(max(5*self.pwmscale, self.pwm.pulse_width() - self.pwmscale * corr))
      else :
      	self.pwm.pulse_width(min(100*self.pwmscale, self.pwm.pulse_width() + self.pwmscale * corr))
  
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
    self.pwm.pulse_width(pct * self.pwmscale)
    self.sleep.on()
  
  """
  Get the current power as a percentage of the max power.
  The result is positive if the motor runs forward, negative if it runs backward.
  """
  def getThrottle(self) :
    thr = self.pwm.pulse_width() // self.pwmscale
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
  Create a controller for a chassis.
  The left motor should be connected to the 'X' pins.
  The right motor should be connected to the 'Y' pins.
  The control ('CTRL') pin of the chassis should be connected to pin X12
  """
  def __init__(self) :
    self.leftmotor = RomiMotor(X=True)
    self.rightmotor = RomiMotor(X=False)
    self.control = Pin('X12', Pin.OUT)
    self.control.value(1)

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
    self.control.value(0)

  """
  Power on the chassis.
  """
  def startup(self) :
    # Drive the control pin high to power the platform
    self.control.value(1)
