# -----------------------------------------------------------
# Copyright (c) SILAB , Physics Institute, University of Bonn
# -----------------------------------------------------------
#
#   This script creates Vivado projects and bitfiles for the supported hardware platforms
#
#   Start vivado in tcl mode by typing:
#       vivado -mode tcl -source run.tcl
#

# Use current environment python instead of vivado included python
unset ::env(PYTHONPATH)
unset ::env(PYTHONHOME)

set vivado_dir [exec pwd]
set basil_dir [exec python -c "import basil, os; print(str(os.path.dirname(os.path.dirname(basil.__file__))))"]
set include_dirs [list $vivado_dir/../src $basil_dir/basil/firmware/modules $basil_dir/basil/firmware/modules/utils]

file mkdir ../bit reports


proc run_bit { part xdc_file size} {
    global vivado_dir

    create_project -force -part $part designs

    read_verilog $vivado_dir/../src/tjmonopix_mio3.v
    read_verilog $vivado_dir/../src/tjmonopix_core.v
    read_edif $vivado_dir/../src/SiTCP/SiTCP_XC7K_32K_BBT_V110.ngc
    read_xdc $xdc_file
    read_xdc $vivado_dir/../src/SiTCP/SiTCP.xdc
    global include_dirs

    synth_design -top tjmonopix_mio3 -include_dirs $include_dirs -verilog_define "SYNTHESIS=1"
    opt_design
    place_design
    phys_opt_design
    route_design
    report_utilization -file "reports/report_utilization.log"
    report_timing -file "reports/report_timing.log"

    write_bitstream -force -bin_file -file $vivado_dir/../bit/tjmonopix_mio3
    write_cfgmem -format mcs -size 64 -interface SPIx4 -loadbit "up 0x0 $vivado_dir/../bit/tjmonopix_mio3.bit" -force -file $vivado_dir/../bit/tjmonopix_mio3
    close_project
}

#
# Create projects and bitfiles
#

#       FPGA type           constraints file               flash size
run_bit xc7k160tfbg676-1    $vivado_dir/../src/tjmonopix_mio3.xdc    64


exit
