#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from tjmonopix.tjmonopix import TJMonoPix
import time

chip = TJMonoPix()
chip['CONF']['DEF_CONF_N'] = 0
chip['CONF'].write()
chip.init()
chip.power_on()
chip.set_inj_amplitude()
#print(chip.get_power_status())

chip['CONF']['RESET_BCID'] = 1
chip['CONF']['RESET'] = 1
chip['CONF'].write()

chip['CONF']['EN_BX_CLK'] = 1
chip['CONF']['EN_OUT_CLK'] = 1
chip['CONF'].write()
 
chip['CONF']['RESET_BCID'] = 0
chip['CONF']['RESET'] = 0
chip['CONF'].write()

chip.default_conf()
chip.set_icasn_low()
#chip.enable_first_column_tst()
#chip.enable_second_column()
#chip.set_test_sim_inj()
#chip.disable_columns()
#chip.set_ireset_high()
#chip.set_ithr_high()
#chip.mask_all()
chip.write_conf()

chip['CONF']['DEF_CONF_N'] = 1
chip['CONF'].write()

#chip.inject()
