# tjmonopix-daq
[![Build Status](https://travis-ci.org/SiLab-Bonn/tjmonopix-daq.svg?branch=development)](https://travis-ci.org/SiLab-Bonn/tjmonopix-daq)

Data acquisition software for the TJMonoPix pixel detector.

# Installation
You need to have python and the following packages installed:
`basil-daq>=3.0.0 bitarray matplotlib numba numpy pytables pyyaml scipy tqdm`

Then run `python setup.py develop` from root folder.

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
