# tjmonopix-daq
[![Build Status](https://travis-ci.org/SiLab-Bonn/tjmonopix-daq.svg?branch=development)](https://travis-ci.org/SiLab-Bonn/tjmonopix-daq)

Data acquisition software for the TJMonoPix pixel detector.

# Installation
You need to have python and the following packages installed:
`basil-daq>=3.0.0 bitarray matplotlib numba numpy pytables pyyaml scipy tqdm`
Then run `python setup.py develop` from root folder.

1. making a GitHub account and push your improvement to Silab-Bonn/tjmonopix-daq is a good idea.
2. install miniconda
    1. miniconda (2.7): [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html)
3. install packages
    1. install packages from conda
       > conda install bitarray matplotlib numba numpy pytables pyyaml scipy tqdm six
    2. basil : 
       [https://github.com/Silab-Bonn/basil](https://github.com/Silab-Bonn/basil)
       > git clone https://github.com/Silab-Bonn/basil  
       > cd basil  
       > python setup.py develop  
4. install packages (optional)
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
4. start notebook
   > cd examples  
   > jupyter notebook  
4. open and run the chip file
5. make yaml file, run scans etc.
6. To restart the notebook, change no_power_reset=True if HV!=0V.
7. Apply HV=0V with current limit of 100uA
8. MIO3, GPAC off
8. Apply PMOS/PWELL = 0V  --> DONE

