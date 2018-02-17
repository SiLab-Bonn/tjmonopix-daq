# tjmonopix-daq
TJ-MonoPix DAQ

#### Important information 
1) /tjmonopix/tjmonopix_mio_v2.bit is a new bitstream that contains the changes in data order - serializer count. However more changes must be made to the firmware e.g. use both A and B I/O.
2) a method called default_conf was added to tjmonopix.py. When called it sets all the registers of CONF_SR to default. (Would it be better if we added the default values at tjmonopix.yaml to read them from there?)

## TODO - PENDING LIST

2) Implement function to read back the configuration (SO_CONF) to check if it is corrupted. This should be the first test after the power-on test of the chip

3) Read data also from input B. Now only data can be read from the first flavor (A). A and B can be connected with jumpers to flavors 1 and 2 or 3 and 4 respectivelly.
	note: The first readout test should be done with flavor 2 (PMOS) because in theory it is more stable.

4) In line #159 of tjmono_data_rx_core: if (RST_SYNC | CONF_EXPOSURE_TIME_RST) //TODO this is not right. What does this mean? is it important?



## FIRST TEST PROCEDURE
1) In a board without the chip, check jumper positions, voltages and currents with the MIO and GPAC connected and on.

2) Power-on test of the chip (no power shorts - normal electrical behavior)
```bash
LATCHUP AVOIDANCE - CHIP POWERUP

A) PCB
	1) Make PSUB PWELL 0.1 or 0 Ohm 220uF or more
	2) Connect backside of PSUB
	3) HV_DIODE to 1.8 together with VDDA

B) Powerup
	1) FPGA on, gpac on powered DEF_CONF_PAD=1
	2) Check very well jumper positions
	2) PSUB, PWELL -3V to -6V, high current limit (several mA)
	3) POWER VDDA, HV_DIODE, then VDDP, VDDA_DAC, VDDD, EXTERNALLY no gpac
	4) Reset the matrix logic and bcid and provide the clocks from the mio.
```


3) Shift in, shift out and confirm configuration is not corrupted

4) Disable all columns, enable test pattern and send READ pulse (or enable columns and inject, but it is better to send a READ PULSE independently of the matrix HIT token), check that the test pattern is received.

5) Inject a row and column of the second flavor and check if we get the correct data
