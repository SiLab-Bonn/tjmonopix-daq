#!/bin/bash
killall pytlu
run=$(/home/silab/miniconda2/envs/tjmonopix/bin/python get_run.py)
date=`date +%y%m%d-%H%M%S`
mkdir -p /sirrush/silab/Data_Testbeams/2018/20180327_tjmonopix_ELSA/run${run}/

##### tjmonopix
gnome-terminal --window --working-directory=/home/silab/tjmonopix/tjmonopix-daq/tjmonopi-daq/tjmonpix/scans -e "/home/silab/miniconda2/envs/tjmonopix/bin/python simple_scan.py  --data /media/silab/HDD1/Testbeam/ELSA_26_03_2018/tjmonopix/tjmonopix${run}_${date} --scan_time $1 &"

#sleep 10
##### tlu
#gnome-terminal --window -e "/home/silab/miniconda2/envs/tjmonopix/bin/pytlu --scan_time=$1 -ie CH0 --timeout=0 --threshold=30 -oe CH0 CH2 -d "

#sleep 3
##### pymosa
#gnome-terminal --window --working-directory=/home/silab/tjmonopix/pymosa/pymosa/ -e "/home/silab/miniconda2/envs/tjmonopix/bin/python m26.py --scan_timeout $1

#sleep 3
##### pyBAR
#cd /home/silab/tjmonopix/pyBAR/pybar/scans/scan_ext_trigger.py;/home/silab/miniconda2/envs/tjmonopix/bin/python scan_ext_trigger.py

#echo "run ${run}, $1 sec"

#cp /media/silab/HDD1/Testbeam/CERN_20_09_2017/monopix_mio3/tlu/tlu_${run}_${date}.log /media/silab/HDD2/testbeam170920/run${run}/
#cp /home/silab/hirono/pyBAR_mimosa/pybar/elsa_20171108/${run}*  /sirrush/silab/Toko/data_elsa_171108/run${run}/
#cp /home/silab/hirono/monopix_mio3/monopix_daq/output_data/simple_scan/*_${run}_simple_scan* /sirrush/silab/Toko/data_elsa_171108/run${run}/
#cp /home/silab/hirono/monopix_mio3/monopix_daq/sitlu*.log /sirrush/silab/Toko/data_elsa_171108/run${run}/
#mv /home/silab/hirono/monopix_mio3/monopix_daq/output_data/simple_scan/*_${run}_simple_scan.h5 /media/silab/HDD1/Testbeam/ELSA_08_11_2017/monopix
#mv /home/silab/hirono/monopix_mio3/monopix_daq/sitlu*.log /media/silab/HDD1/Testbeam/ELSA_08_11_2017/tlu
