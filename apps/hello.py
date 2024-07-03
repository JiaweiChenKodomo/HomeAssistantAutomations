import appdaemon.plugins.hass.hassapi as hass

import time

import datetime as dt


#
# Hellow World App
#
# Args:
#

class HelloWorld(hass.Hass):

  check_people_freq = 30 #sec
  check_illum_freq = 10 #sec
  check_illum_time = 5 #times
  turnOffHiLAfter = 600 #sec
  #turnOffHiLAfter = 10 #sec
  false_trigger_interval = 30 #sec
  table_illum = 800 #lux
  table_illum2 = 800 #lux
  #table_illum = 500 - 250 #lux, increased to accomodate for slight overestimation in HiL due to modeling simplification.
  max_light_illum =  716.7 #lux. Measured with luxmeter onsite.
  max_light_illum2 =  716.7 #lux. Measured with luxmeter onsite.
  max_flourescent_illum = 784 #lux. Illuminance contribution from flourescent light.
  old = 0 # Previous light level
  old2 = 0 # Previous light level for second led
  #old_fp2 = 0 # Previous FP2 lux reading. Checks whether flourescent light is on.
  flourescent_illum = 0.0
  delta_fp2 = 60 #lux. Change in FP2 illuminance due to flourescent light.

  turn_off_poll = [0, 0] # Polling to see if need to turn off flourescent light. If both desks agree to turn off, then turn off.

  def initialize(self):
    #self.log("Hello from AppDaemon")
    #self.log("You are now ready to run Apps!")
    self.last_time = time.time()
    self.HiL_handle = None
    # Initialize automation settings and illuminance set level.
    self.set_value("input_number.illuminance_set_level", self.table_illum)
    self.set_value("input_number.illuminance_set_level2", self.table_illum2)
    self.turn_on("input_boolean.useautomation")
    self.turn_off("input_boolean.useautomation2")
    # Initial FP2 lux reading. Checks whether flourescent light is on.
    #self.old_fp2 = float(self.get_state("sensor.presence_sensor_fp2_4a6e_light_sensor_light_level"))
    # Will turn off system if found people left. (Note: listen_state can't be nested!)
    self.listen_state(self.turnOffSys, "binary_sensor.my_presence_sensor", old = "on", new = "off", duration = self.false_trigger_interval)
    # Current setup controls the on/off state of sensor through HASS automation.
    #self.run_daily(self.turnOffHiLTimed, dt.time(17,30,0))
    
    # Will turn on system if found people arrive. (Note: listen_state can't be nested!)
    self.listen_state(self.turnOnSys, "binary_sensor.my_presence_sensor", old = "off", new = "on")
    #self.run_daily(self.turnOnHiLTimed, dt.time(7,00,0))

  def turnOnSys(self, entity, attribute, old, new, cb_args):
    #self.log("Turn on system!")
    # Turn on HiL sensor.
    #self.turn_on("switch.lamp")
    #self.turn_on("switch.rpi_hil_data")
    # Start a loop to check if people around and conduct simulation every check_people_freq.
    if self.HiL_handle:
      #self.log("Clear handle!")
      # Clearing handle is needed as turnOffSys is not triggered when sensor state changes in turnOnLight (due to racing?). 
      # In this case multiple processes running startHiL are generated.
      self.cancel_timer(self.HiL_handle)
      self.HiL_handle = None
    self.HiL_handle = self.run_every(self.startHiL, "now", self.check_people_freq)

  def turnOnHiLTimed(self, cb_args):
    #self.log("Turn on system!")
    # Turn on HiL sensor.
    self.turn_on("switch.lamp")
    self.turn_on("switch.rpi_hil_data")

  def turnOffSys(self, entity, attribute, old, new, cb_args):
    now_time = time.time()
    doAuto = self.get_state("input_boolean.useautomation")
    doAuto2 = self.get_state("input_boolean.useautomation2")
    new = self.get_state("binary_sensor.my_presence_sensor")
    if new == "off":
      # There is no one in all two cubicles.
      #if now_time - self.last_time > self.false_trigger_interval:
      self.log("Turn down light due to people exiting!")
      if doAuto == "on":
        self.turn_off("light.0x001788010d7103db")
        if doAuto2 == "on":
          self.turn_off("light.0x001788010d455ffd")
          #self.turn_off("input_boolean.fluorescent_state")
          self.turn_off("switch.0x54ef44100081977f")
      elif doAuto2 == "on":
        self.turn_off("light.0x001788010d455ffd")
      self.last_time = now_time
      self.old = 0
      # Turn off the check loop as well.
      if self.HiL_handle:
        self.log("Turn off check loop and clear handle!")
        self.cancel_timer(self.HiL_handle)
        self.HiL_handle = None
      # Turn off sensor system if left for more than turnOffHiLAfter sec.
      #self.log("Turn off HiL system later.")
      #self.run_in(self.turnOffHiL, self.turnOffHiLAfter)
      # else:
      #   # Add this because Presence sensor may be falsely triggered
      #   self.log("Too frequently triggered with presence 1&&2 set to off!")

  def turnOffHiLTimed(self, cb_args):
    # There is no one. Turn off the HiL simulation
    self.log("Turn off HiL system!")
    self.turn_off("switch.lamp")
    self.turn_off("switch.rpi_hil_data")
    
    
  def turnOffHiL(self, cb_args):
    self.log("Check if need to turn off HiL system!")
    #elapsed_time = time.time() - self.last_time
    #self.log("Elapsed time is {}".format(elapsed_time))
    #if elapsed_time < self.turnOffHiLAfter:
      #time.sleep(self.turnOffHiLAfter - elapsed_time)
    now = self.get_state("binary_sensor.my_presence_sensor")
    if now == "off":
      # There is no one. Turn off the HiL simulation
      self.log("Turn off HiL system!")
      self.turn_off("switch.lamp")
      self.turn_off("switch.rpi_hil_data")

  def startHiL(self, cb_args):
    now_time = time.time()
    self.log("Checked at {}".format(now_time))
    new = self.get_state("binary_sensor.presence_sensor_fp2_4a6e_presence_sensor_2")
    doAuto = self.get_state("input_boolean.useautomation")
    new2 = self.get_state("binary_sensor.presence_sensor_fp2_4a6e_presence_sensor_3")
    doAuto2 = self.get_state("input_boolean.useautomation2")
    if doAuto == "on" and new == "off":
      # There is no one.
      if now_time - self.last_time > self.false_trigger_interval:
        self.log("No one is detected at 1!")
        self.turn_off("light.0x001788010d7103db")
        #self.checkRound = 0
        self.old = 0
        # Declare that can turn off fluorescent light.
        self.turn_off_poll[0] = 1
      else:
        # Add this because Presence sensor may be falsely triggered
        self.log("Too frequently triggered with presence set to off 1!")
    elif doAuto == "on":
      # There is people, so conduct simulation for a while.
      #self.log("Start HiL Simulation!")
      self.turnOnLight()
    else:
      self.log("Automation turned off for 1!")

    if doAuto2 == "on" and new2 == "off":
      # There is no one.
      if now_time - self.last_time > self.false_trigger_interval:
        self.log("No one is detected at 2!")
        self.turn_off("light.0x001788010d455ffd")
        #self.checkRound = 0
        self.old2 = 0
        # Declare that can turn off fluorescent light.
        self.turn_off_poll[1] = 1
      else:
        # Add this because Presence sensor may be falsely triggered
        self.log("Too frequently triggered with presence set to off 2!")
    elif doAuto2 == "on":
      # There is people, so conduct simulation for a while.
      # self.log("Start HiL Simulation!")
      self.turnOnLight2()
    else:
      self.log("Automation turned off for 2!")
    self.last_time = now_time

  def turnOnLight(self):
    #now_time = time.time()
    doAuto2 = self.get_state("input_boolean.useautomation2")
    new = self.get_state("sensor.my_tcp_sensor1") 
    self.log("Illuminance is: {illu}".format(illu = new))
    self.turn_off_poll[0] = 0 # Initialize own choice of turning off fluorescent or not. No risk of racing.

    # Deals with fluorescent ligt. 
    fp2_illum = self.get_state("switch.0x54ef44100081977f")
    if (fp2_illum) == 'on':
      # 
      self.log("Fluorescent light is on.")
      self.flourescent_illum = self.max_flourescent_illum
      #self.turn_on("input_boolean.fluorescent_state")
    else:
      # FP2 reading drops by delta_fp2 lux. Regard as flourescent light off.
      self.flourescent_illum = 0
      self.log("Fluorescent light is off.")
      #self.turn_off("input_boolean.fluorescent_state")
    #self.old_fp2 = float(fp2_illum)
    self.log("Flourescent light contribution is: {}".format(self.flourescent_illum))

    self.table_illum = float(self.get_state("input_number.illuminance_set_level"))
    self.log("Illuminance set level is {}".format(self.table_illum))

    if (self.max_light_illum + float(new)) < self.table_illum:
      # Need to turn on fluorescent light.
      #self.turn_on("input_boolean.fluorescent_state")
      self.turn_on("switch.0x54ef44100081977f")
      self.flourescent_illum = self.max_flourescent_illum
      self.turn_off_poll[0] = 0 # Declare that don't want to turn off.

    elif doAuto2 == "on" and (self.turn_off_poll[1] == 1):
      self.turn_off_poll[0] = 1
      #self.turn_off("input_boolean.fluorescent_state")
      self.turn_off("switch.0x54ef44100081977f")
      self.flourescent_illum = 0 
    else:
      self.turn_off_poll[0] = 1

    if (float(new) + self.flourescent_illum) < self.table_illum:
      self.log("Update light level!")
      #new_bright = int(min(255 * (self.table_illum - float(new) - self.flourescent_illum) / self.max_light_illum, 255))
      new_bright = self.Illu2LEDSetLevel(self.table_illum - float(new) - self.flourescent_illum)
      self.log("New brightness is: {}".format(new_bright))
      self.set_value("input_number.led_level", new_bright)
      bright_diff = new_bright - self.old
      if bright_diff > 0:
        # graduately tune up light
        for aa in range(bright_diff):
          time.sleep(0.01)
          #self.log("Set brightness (increasing): {}".format(self.old + aa + 1))
          self.turn_on("light.0x001788010d7103db", brightness = self.old + aa + 1)
      elif bright_diff < 0:
        # graduately tune down light
        for aa in range(-bright_diff):
          time.sleep(0.01)
          #self.log("Set brightness (decreasing): {}".format(self.old - aa - 1))
          self.turn_on("light.0x001788010d7103db", brightness = self.old - aa - 1)
      #self.turn_on("light.0x001788010d7103db", brightness = new_bright)
      self.old = new_bright
    else:
      #self.log("Turn down light due to enough daylight!")
      self.turn_off("light.0x001788010d7103db")
      self.old = 0
    #self.last_time = now_time


  def turnOnLight2(self):
    #now_time = time.time()
    new = self.get_state("sensor.my_tcp_sensor2") 
    #self.log("Illuminance is: {illu}".format(illu = new))
    doAuto = self.get_state("input_boolean.useautomation")
    self.turn_off_poll[1] = 0 # Initialize own choice of turning off fluorescent or not. No risk of racing.

    fp2_illum = self.get_state("switch.0x54ef44100081977f")
    #self.log("FP2 reading of illuminance is: {}".format(fp2_illum))
    #self.log("Previous FP2 reading of illuminance is: {}".format(self.old_fp2))
    if (fp2_illum) == "on":
      self.log("Fluorescent light is on.")
      self.flourescent_illum = self.max_flourescent_illum
      #self.turn_on("input_boolean.fluorescent_state")
    else:
      self.log("Fluorescent light is off.")
      self.flourescent_illum = 0
      #self.turn_off("input_boolean.fluorescent_state")
    #self.old_fp2 = float(fp2_illum)
    #self.log("Flourescent light contribution is: {}".format(self.flourescent_illum))

    self.table_illum2 = float(self.get_state("input_number.illuminance_set_level2"))
    #self.log("Illuminance set level is {}".format(self.table_illum2))

    if (self.max_light_illum2 + float(new)) < self.table_illum2:
      # Need to turn on fluorescent light.
      #self.turn_on("input_boolean.fluorescent_state")
      self.turn_on("switch.0x54ef44100081977f")
      self.flourescent_illum = self.max_flourescent_illum
      self.turn_off_poll[1] = 0 # Declare that don't want to turn off.
    elif doAuto == "on" and (self.turn_off_poll[0] == 1):
      self.turn_off_poll[1] = 1
      #self.turn_off("input_boolean.fluorescent_state")
      self.turn_off("switch.0x54ef44100081977f")
      self.flourescent_illum = 0
    else:
      self.turn_off_poll[1] = 1

    if (float(new) + self.flourescent_illum) < self.table_illum2:
      self.log("Update light level at 2!")
      new_bright = self.Illu2LEDSetLevel(self.table_illum2 - float(new) - self.flourescent_illum)
      #new_bright = int(min(255 * (self.table_illum2 - float(new) - self.flourescent_illum) / self.max_light_illum2, 255))
      self.log("New brightness is: {} at 2".format(new_bright))
      self.set_value("input_number.led_level2", new_bright)
      bright_diff = new_bright - self.old2
      if bright_diff > 0:
        # graduately tune up light
        for aa in range(bright_diff):
          time.sleep(0.01)
          #self.log("Set brightness (increasing): {}".format(self.old2 + aa + 1))
          self.turn_on("light.0x001788010d455ffd", brightness = self.old2 + aa + 1)
      elif bright_diff < 0:
        # graduately tune down light
        for aa in range(-bright_diff):
          time.sleep(0.01)
          #self.log("Set brightness (decreasing): {}".format(self.old2 - aa - 1))
          self.turn_on("light.0x001788010d455ffd", brightness = self.old2 - aa - 1)
      self.old2 = new_bright
    else:
      #self.log("Turn down light due to enough daylight!")
      self.turn_off("light.0x001788010d455ffd")
      self.old2 = 0
    #self.last_time = now_time
    #################################################

  def Illu2LEDSetLevel(self, illum):
    k = 1.743582924067780
    a = 0.045637875322394
    self.log("illum = {}".format(illum))
    #return 10
    if illum <= 0:
      return 0
    else:
      return min(int(round((illum/a)**(1/k))), 255)