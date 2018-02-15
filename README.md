# tjmonopix-daq
TJ-MonoPix DAQ

## Important information -  we need to generate a new bitstream with the changes in the firmware (data order - serializer count) before doing the first test

## TODO - PENDING LIST
1) Default configuration is not sent to the chip. Only the registers we want to change and define at test_Sim.py are sent. The rest are 0. 
	```bash 
	This is very important and we cannot test the chip if not fixed.
	```
note: should we add the default values at tjmonopix.yaml to read them from there?)

2) Implement function to read back the configuration (SO_CONF) to check if it is corrupted. This should be the first test after the power-on test of the chip

3) Read data also from input B. Now only data can be read from the first flavor (A). A and B can be connected with jumpers to flavors 1 and 2 or 3 and 4 respectivelly.
	note: The first readout test should be done with flavor 2 (PMOS) because in theory it is more stable.

4) In line #159 of tjmono_data_rx_core: if (RST_SYNC | CONF_EXPOSURE_TIME_RST) //TODO this is not right. What does this mean? is it important?



## FIRST TEST PROCEDURE
1) In a board without the chip, check jumper positions, voltages and currents with the MIO and GPAC connected and on.

2) Power-on test of the chip (no power shorts - normal electrical behavior)

3) Shift in, shift out and confirm configuration is not corrupted

4) Disable all columns, enable test pattern and send READ pulse (or inject, but it is better to send a READ PULSE independently of the matrix HIT token), check that the test pattern is received.

5) Inject a row and column of the second flavor and check if we get the correct data
