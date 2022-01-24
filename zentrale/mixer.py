#!/usr/bin/env python3

from drv8830 import DRV8830
import threading
from threading import Thread
import time
import logging


logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)


class mixer():
    def __init__(self, addr=0x64):
        '''Init object mixer
        min_ff_temp: minimum forward flow temperature
        max_ff_temp: maximum forward flow temperature
        mix_close: closing time of mixer
        mix_open: opening time of mixer
        mix_pause: wait time to let new temperature settle
        ff_temp_target_val: forward flow target temperature
        ff_temp_is_val: forward flow is temperature
        hyst: temperature hystere
        addr: I2C address of motor driver, defaults to 0x64
        voltage: motor voltage
        '''
        threading.Thread.__init__(self)
        self.running = False
        self.min_ff_temp = 28
        self.max_ff_temp = 34
        self.mix_time_c = .1
        self.mix_time_m = .1
        self.mix_time_f = .05
        self.mix_pause_c = 5 
        self.mix_pause_f = 10
        self.ff_temp_target_val = 30
        self.ff_temp_is_val = 31
        self.hyst = .5

        self.addr = addr
        self.voltage = 3.3
        self.mot = DRV8830(self.addr)
        self.mix_t_stop = threading.Event()

    @property
    def ff_temp_target(self) -> float:
        return self.ff_temp_target_val


    @ff_temp_target.setter
    def ff_temp_target(self, is_temp:float):
        '''This function returns the value of the forward flow temperature
        which correspondends to the measured actual otuside temperature
        '''
        ff_temp = -0.18 * is_temp + 31.24
        if(ff_temp < self.min_ff_temp):
            ff_temp = self.min_ff_temp
        if(ff_temp > self.max_ff_temp):
            ff_temp = self.max_ff_temp
        self.ff_temp_target_val = ff_temp
        logger.debug("ff_temp_target_val = " + str(self.ff_temp_target_val) + "°C")

    @property
    def ff_temp_is(self) -> float:
        return self.ff_temp_is_val

    @ff_temp_is.setter
    def ff_temp_is(self, is_temp:float):
        '''Function to set the measured forward flow temperature
        '''
        self.ff_temp_is_val = is_temp

    def is_running(self) -> bool:
        '''Returns if the mixer thread is running or not
        Return: true/false
        '''
        return self.running

    def warmer(self, hold):
        '''Driving the mixer open for time mix_open
        to increase forward flow temperature
        '''
        self.mot.set_voltage(self.voltage)
        self.mot.forward()
        time.sleep(hold)
        self.mot.coast()
        self.mot.set_voltage(0)
        logger.debug("Mixer warmer")

    def colder(self, hold):
        '''Driving the mixer close for time mix_close
        to decrease forward flow temperature
        '''
        self.mot.set_voltage(self.voltage)
        self.mot.reverse()
        time.sleep(hold)
        self.mot.coast()
        self.mot.set_voltage(0)
        logger.debug("Mixer colder")

    def run(self):
        mixT = threading.Thread(target=self._run)
        mixT.setDaemon(True)
        mixT.start()

    def _run(self):
        logger.info("Starting Forward Flow Mixer")
        self.running = True
        self.mix_t_stop.clear()
        while(not self.mix_t_stop.is_set()):
            logger.debug("FF Temp: "+str(self.ff_temp_is))
            diff = self.ff_temp_is - self.ff_temp_target
            logger.debug("Diff = " + str(diff) + "°C")
            if(abs(diff) < 5):
                pause = self.mix_pause_f
                hold = self.mix_time_f
           # elif(diff < abs(5)):
           #     hold = self.mix_time_m
            else:
                pause = self.mix_pause_c
                hold = self.mix_time_c
            logger.debug("Setting motor time to " + str(hold) +"s")
            logger.debug("Setting pause time to " + str(pause) +"s")
            
            if(self.ff_temp_is < self.ff_temp_target - self.hyst/2):
                self.warmer(hold)
            elif(self.ff_temp_is > self.ff_temp_target + self.hyst/2):
                self.colder(hold)
            else:
                pass
            self.mix_t_stop.wait(pause)

    def stop(self):
        self.running = False
        logger.info("Stopping Forward Flow Mixer")
        self.mix_t_stop.set()


if(__name__ == "__main__"):
    mix = mixer()
    print(mix.ff_temp_target)
    mix.ff_temp_target = -3
    print(mix.ff_temp_target)

    print(mix.ff_temp_is)
    mix.ff_temp_is = 313
    print(mix.ff_temp_is)

    mix.warmer()
    print(mix.ff_temp_is)
