import zlib # workaround
import yaml
import logging
import os
import time
import basil
from basil.dut import Dut
from basil.utils.BitLogic import BitLogic
#import pkg_resources

loglevel = logging.DEBUG
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.getLogger('basil.HL.RegisterHardwareLayer').setLevel(logging.WARNING)

logging.basicConfig(format="%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s")
    
logger = logging.getLogger('TJMONOPIX')
logger.setLevel(loglevel)


class power_supply(Dut):    

    def __init__(self, conf=None, **kwargs):

        self.proj_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        if not conf:
            conf = os.path.join(self.proj_dir, 'instrumentation' +
                                os.sep + 'power_supply.yaml')

        logger.debug("Loading configuration file from {:s}".format(conf))

        super(power_supply, self).__init__(conf)

    def init(self):
        super(power_supply, self).init()

    def power_on(self, **kwargs):
            if not self:
                logger.debug('No powersupply defined.')
                return

            try:
                set_up = False
                for ps in self:
                    if not isinstance(ps, basil.RL.FunctionalRegister.FunctionalRegister):
                        continue
                    voltage = kwargs.get(ps.name)
                    cur_lim = kwargs.get(ps.name + '_cur_lim', 0.5)

                    if not voltage:
                        logger.debug('Value for %s is not defined!' % ps.name)
                        continue

                    logger.debug('Set channel %s to %1.3fV with current limit %1.3fA' % (ps.name, voltage, cur_lim))

                    ps.set_voltage(voltage)
                    ps.set_current_limit(cur_lim)

                    ps.set_enable(on=True)
                    set_up = True

                if set_up: 
                    logger.info('Set up powersupply %s' % (self['SCC_Powersupply'].get_info()))
            except KeyError as e:
                logger.error('There was an error setting up the powersupply: %s' % e)


    def power_on_left_default(self):
	self['VDD_LEFT'].set_voltage(5)
        self['VDD_LEFT'].set_current_limit(1.2)
	self['VDD_LEFT'].set_enable(on=True)

    def power_on_right_default(self):
	self['VDD_RIGHT'].set_voltage(1.8)
        self['VDD_RIGHT'].set_current_limit(0.01)
	self['VDD_RIGHT'].set_enable(on=True)

    def power_off(self, ps):
        if not self:
            logger.debug('No powersupply defined.')
            return
        try:
            logger.debug('Turn off channel %s' % (ps))

            self[ps].set_enable(on=False)
                    
            logger.info('Set up powersupply %s' % (self['SCC_Powersupply'].get_info()))
        except KeyError:
            logger.debug('No powersupply found.')
	
    def power_off_all(self):
	for pwr in ['VDD_LEFT', 'VDD_RIGHT']:
	    self[pwr].set_enable(on=False)

    def get_power_status(self, log=False):
        status = {}
        for pwr in ['VDD_LEFT', 'VDD_RIGHT']:
            status[pwr+' [V]'] = self[pwr].get_voltage()
            status[pwr+' [A]'] = self[pwr].get_current()

        return status



class sourcemeter2450(Dut):    

    def __init__(self, conf=None, **kwargs):

        self.proj_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        if not conf:
            conf = os.path.join(self.proj_dir, 'instrumentation' +
                                os.sep + 'keithley2450_pyvisa.yaml')

        logger.debug("Loading configuration file from {:s}".format(conf))

        super(sourcemeter2450, self).__init__(conf)

    def init(self):
        super(sourcemeter2450, self).init()


class sourcemeter2634(Dut):    

    def __init__(self, conf=None, **kwargs):

        self.proj_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        if not conf:
            conf = os.path.join(self.proj_dir, 'instrumentation' +
                                os.sep + 'keithley2634_pyvisa.yaml')

        logger.debug("Loading configuration file from {:s}".format(conf))

        super(sourcemeter2634, self).__init__(conf)

    def init(self):
        super(sourcemeter2634, self).init()

