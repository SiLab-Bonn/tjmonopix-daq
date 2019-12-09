# tjmonopix-daq
[![Build Status](https://travis-ci.org/SiLab-Bonn/tjmonopix-daq.svg?branch=development)](https://travis-ci.org/SiLab-Bonn/tjmonopix-daq)

Data acquisition software for the TJMonoPix pixel detector.

# Installation
You need to have python and the following packages installed:
`basil-daq>=3.0.0 bitarray matplotlib numba numpy pytables pyyaml scipy tqdm`
Then run `python setup.py develop` from root folder.

1. Making a GitHub account and push your improvement to Silab-Bonn/tjmonopix-daq is a good idea.
2. Install miniconda
    1. miniconda (2.7): [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html)
3. Install packages
    1. Install packages from conda
       > conda install bitarray matplotlib numba numpy pytables pyyaml scipy tqdm six
    2. basil : 
       [https://github.com/Silab-Bonn/basil](https://github.com/Silab-Bonn/basil)
       > git clone https://github.com/Silab-Bonn/basil  
       > cd basil  
       > python setup.py develop  
4. Install packages (optional)
    1. online_monitor : 
       [https://github.com/Silab-Bonn/online_monitor](https://github.com/Silab-Bonn/online_monitor)
       > conda install pzmq psutil pzqtgraph nose testfixtures  
       > git clone https://github.com/Silab-Bonn/online_monitor  
       > python setup.py develop  
    2. pixle_clusterizer : [https://github.com/Silab-Bonn/pixle_clusterizer](https://github.com/Silab-Bonn/pixle_clusterizer)
       > git clone https://github.com/Silab-Bonn/pixle_clusterizer  
       > cd pixle_clusterizer  
       > python setup.py develop  
    3. jupyter, notebook:
       > conda install jupyter, notebook  

# Usage
To run a scan, create a YAML file with the configuration, for example:
```yaml
dut :
    flavor: "PMOS"
    vreset_dacunits : 35
    icasn_dacunits : 0
    ireset_dacunits :
        value: 29
        mode: 0
    ithr_dacunits : 15
    idb_dacunits : 30
    ibias_dacunits : 45

scan :
    online_onitor: "tcp://127.0.0.1:5500"

mask:
    [
        [1, 10, 177],
        [1, 106, 177]
    ]
```
It contains the DUT settings as well as addresses for [Online Monitor](https://github.com/SiLab-Bonn/online_monitor) and the option to mask specific pixels.

# Getting start (PMOS flavor)

1. Apply HV=0V with current limit of 100uA
2. Apply PMOS/PWELL=-6V with current limit of 200uA
3. Apply MIO3=6V, GPAC=5V and wait for LED=ON
4. Start notebook
   > cd examples  
   > jupyter notebook  
4. Open and run the chip file
5. Make yaml file, run scans, and etc.
6. To restart the notebook, change no_power_reset=True if HV!=0V.
7. Apply HV=0V with current limit of 100uA
8. MIO3, GPAC off
8. Apply PMOS/PWELL = 0V  --> DONE

# How to update firmware
1. Install vivado (tested version: 2016.1)
2. Download SiTCP files
3. Install drivers for JTAG
2. Open vivado project file: firmware/src/tjmonopix_mio3.xpr
3. Add basil module directrories to the search path
3. Generate a bit file
4. Connect JTAG and run Hardware Manager
5. Add flash memory
6. Write to the flash

# How to make firmware (MIO3)
1. install vivado 
    1. Web (free) version is OK
    2. 2016.1 has been tested
2. Download SiTCP netlist
    1. https://github.com/BeeBeansTechnologies/SiTCP_Netlist_for_Kintex7
    3. Put all files in firmware/src/SiTCP
2. Start vivado, open project and select firmware/vivado/tjmonopix.xpr
3. In Flow Manager -> Project Manager->Project Setting -> General -> Language Options -> Verilog options
    1. delete all basil directories in Verilog Include Files Search Paths
    2. add basil directories 
         1. <path_to_basil>/basil/firmware/modules
         2. <path_to_basil>/basil/firmware/modules/utils
4. Click Flow Manager -> Program and Debug -> Generates Bitstream
5. Program FPGA 
    1. Right click Flow Manager -> Program and Debug -> Hardware manager -> Open Target
    2. then select AutoConnect
    3. Right click xc7k160t
    4. Select Program. A window will pop-up. Select bit file
    5. Click OK
6. Write to Flash
    0. add register
    1. Right click at xc7k160t_0
    2. Add flash (n25q256-3.3v-spi-x1_x2_x4)_
    3. Select bin file
    4. Select pull-up 
    5. Click OK and wait a bit



