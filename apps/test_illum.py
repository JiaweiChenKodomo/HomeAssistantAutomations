import appdaemon.plugins.hass.hassapi as hass

import time

import datetime as dt


#
# Test Energy App
#
# Args:
#

class TestIllum(hass.Hass):

  check_freq = 60 #sec

  totalStep = 400
  current_step = 0

  setLevelLst = [0,25,51,76,102,127,153,178,204,229,255,229,204,178,153,127,102,76,51,25]
  
  def initialize(self):
    #self.log("Hello from AppDaemon")
    #self.log("You are now ready to run Apps!")
    self.last_time = time.time()
    self.HiL_handle = self.run_every(self.adjLevel, "now", self.check_freq)

  def adjLevel(self, cb_args):
    #Adjust LED level at set intervals.
    if self.current_step < self.totalStep:
        setLevel = self.setLevelLst[self.current_step%20]
        self.log("Set level is: {}".format(setLevel))
        self.turn_on("light.0x001788010d7103db", brightness = setLevel)
        self.current_step += 1
    else:
        self.cancel_timer(self.HiL_handle)
        self.HiL_handle = None
