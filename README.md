# tjmonopix-daq
TJ-MonoPix DAQ

# TEST PROCEDURE
1) In a board without the chip, check jumper positions, voltages and currents with the MIO and GPAC connected and on.

2) Power-on test of the chip
	a) Bias PWELL and PSUB to -3V (optimal but can be from 0 to -6)

3) Monopix.ipynb (jupyter notebook) contains the code to initialize the MIO, GPAC and TJ-Monopix and provides usefull code samples such as injection, s-curve measurement, etc
