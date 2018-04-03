# constrains based on MIO ucf file
# ------ Constraints
# FCLK (100 MHz)
set_property PACKAGE_PIN AA3 [get_ports FCLK_IN]
set_property IOSTANDARD LVCMOS15 [get_ports FCLK_IN]
create_clock -period 10.000 -name FCLK_IN -add [get_ports FCLK_IN]

set_false_path -from [get_clocks CLK40_PLL] -to [get_clocks BUS_CLK_PLL]
set_false_path -from [get_clocks BUS_CLK_PLL] -to [get_clocks CLK40_PLL]

set_false_path -from [get_clocks CLK160_PLL] -to [get_clocks BUS_CLK_PLL]
set_false_path -from [get_clocks BUS_CLK_PLL] -to [get_clocks CLK160_PLL]

#set_false_path -from [get_clocks CLK16_PLL] -to [get_clocks BUS_CLK_PLL]
#set_false_path -from [get_clocks BUS_CLK_PLL] -to [get_clocks CLK16_PLL]

set_false_path -from [get_clocks CLK8_PLL] -to [get_clocks BUS_CLK_PLL]
set_false_path -from [get_clocks BUS_CLK_PLL] -to [get_clocks CLK8_PLL]

create_clock -period 8.000 -name rgmii_rxc -add [get_ports rgmii_rxc]
set_false_path -from [get_clocks CLK125PLLTX] -to [get_clocks BUS_CLK_PLL]
set_false_path -from [get_clocks BUS_CLK_PLL] -to [get_clocks CLK125PLLTX]
set_false_path -from [get_clocks BUS_CLK_PLL] -to [get_clocks rgmii_rxc]
set_false_path -from [get_clocks rgmii_rxc] -to [get_clocks BUS_CLK_PLL]

# ------ LED
set_property PACKAGE_PIN M17 [get_ports {LED[0]}]
set_property PACKAGE_PIN L18 [get_ports {LED[1]}]
set_property PACKAGE_PIN L17 [get_ports {LED[2]}]
set_property PACKAGE_PIN K18 [get_ports {LED[3]}]
set_property PACKAGE_PIN P26 [get_ports {LED[4]}]
set_property PACKAGE_PIN M25 [get_ports {LED[5]}]
set_property PACKAGE_PIN L25 [get_ports {LED[6]}]
set_property PACKAGE_PIN P23 [get_ports {LED[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports LED*]
set_property SLEW SLOW [get_ports LED*]

# ------ Button & Spare & more - omitted for now
set_property PACKAGE_PIN C18 [get_ports RESET_N]
set_property IOSTANDARD LVCMOS33 [get_ports RESET_N]
set_property PULLUP true [get_ports RESET_N]

# ------ I2C control signals
set_property PACKAGE_PIN P24 [get_ports SDA]
set_property IOSTANDARD LVCMOS33 [get_ports SDA]
set_property PACKAGE_PIN N24 [get_ports SCL]
set_property IOSTANDARD LVCMOS33 [get_ports SCL]

# ------ Trigger IOs - partial (MIO3 has fewer lemo than MIO)
set_property PACKAGE_PIN AB21 [get_ports {LEMO_TX[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {LEMO_TX[0]}]
set_property PACKAGE_PIN V23 [get_ports {LEMO_TX[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {LEMO_TX[1]}]
set_property PACKAGE_PIN U22 [get_ports {LEMO_RX[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {LEMO_RX[0]}]
set_property PACKAGE_PIN U26 [get_ports {LEMO_RX[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {LEMO_RX[1]}]

# ------ Async SRAM - omitted for now
# SRAM faked with SiTCP

# ------ RGMII
set_property SLEW FAST [get_ports mdio_phy_mdc]
set_property IOSTANDARD LVCMOS33 [get_ports mdio_phy_mdc]
set_property PACKAGE_PIN N16 [get_ports mdio_phy_mdc]

set_property SLEW FAST [get_ports mdio_phy_mdio]
set_property IOSTANDARD LVCMOS33 [get_ports mdio_phy_mdio]
set_property PACKAGE_PIN U16 [get_ports mdio_phy_mdio]

set_property SLEW FAST [get_ports phy_rst_n]
set_property IOSTANDARD LVCMOS33 [get_ports phy_rst_n]
set_property PACKAGE_PIN M20 [get_ports phy_rst_n]

set_property IOSTANDARD LVCMOS33 [get_ports rgmii_rxc]
set_property PACKAGE_PIN R21 [get_ports rgmii_rxc]

set_property IOSTANDARD LVCMOS33 [get_ports rgmii_rx_ctl]
set_property PACKAGE_PIN P21 [get_ports rgmii_rx_ctl]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_rxd[0]}]
set_property PACKAGE_PIN P16 [get_ports {rgmii_rxd[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_rxd[1]}]
set_property PACKAGE_PIN N17 [get_ports {rgmii_rxd[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_rxd[2]}]
set_property PACKAGE_PIN R16 [get_ports {rgmii_rxd[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_rxd[3]}]
set_property PACKAGE_PIN R17 [get_ports {rgmii_rxd[3]}]

set_property SLEW FAST [get_ports rgmii_txc]
set_property IOSTANDARD LVCMOS33 [get_ports rgmii_txc]
set_property PACKAGE_PIN R18 [get_ports rgmii_txc]

set_property SLEW FAST [get_ports rgmii_tx_ctl]
set_property IOSTANDARD LVCMOS33 [get_ports rgmii_tx_ctl]
set_property PACKAGE_PIN P18 [get_ports rgmii_tx_ctl]

set_property SLEW FAST [get_ports {rgmii_txd[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_txd[0]}]
set_property PACKAGE_PIN N18 [get_ports {rgmii_txd[0]}]
set_property SLEW FAST [get_ports {rgmii_txd[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_txd[1]}]
set_property PACKAGE_PIN M19 [get_ports {rgmii_txd[1]}]
set_property SLEW FAST [get_ports {rgmii_txd[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_txd[2]}]
set_property PACKAGE_PIN U17 [get_ports {rgmii_txd[2]}]
set_property SLEW FAST [get_ports {rgmii_txd[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {rgmii_txd[3]}]
set_property PACKAGE_PIN T17 [get_ports {rgmii_txd[3]}]

# ------ Debugging - empty in old ucf

# ------ GPAC IOs

#set_property PACKAGE_PIN G20 [get_ports {DOUT[19]}]
#set_property PACKAGE_PIN H19 [get_ports {DOUT[18]}]
#set_property PACKAGE_PIN J16 [get_ports {DOUT[17]}]
#set_property PACKAGE_PIN J15 [get_ports {DOUT[16]}]
#set_property PACKAGE_PIN F15 [get_ports {DOUT[15]}]
#set_property PACKAGE_PIN G15 [get_ports {DOUT[14]}]
#set_property PACKAGE_PIN N22 [get_ports {DOUT[13]}]
#set_property PACKAGE_PIN N21 [get_ports {DOUT[12]}]
#set_property PACKAGE_PIN Y21 [get_ports {DOUT[11]}]
#set_property PACKAGE_PIN W20 [get_ports {DOUT[10]}]
#set_property PACKAGE_PIN AC22 [get_ports {DOUT[9]}]
#set_property PACKAGE_PIN AB22 [get_ports {DOUT[8]}]
#set_property PACKAGE_PIN W24 [get_ports {DOUT[7]}]
#set_property PACKAGE_PIN W23 [get_ports {DOUT[6]}]
#set_property PACKAGE_PIN U25 [get_ports {DOUT[5]}]
#set_property PACKAGE_PIN U24 [get_ports {DOUT[4]}]
#set_property PACKAGE_PIN M26 [get_ports {DOUT[3]}]
#set_property PACKAGE_PIN N26 [get_ports {DOUT[2]}]
#set_property PACKAGE_PIN AE21 [get_ports {DOUT[1]}]
#set_property PACKAGE_PIN AD21 [get_ports {DOUT[0]}]
#set_property IOSTANDARD LVCMOS33 [get_ports "DOUT*"]

#set_property PACKAGE_PIN H17 [get_ports {DIN[11]}]
#set_property PACKAGE_PIN E15 [get_ports {DIN[10]}]
#set_property PACKAGE_PIN H18 [get_ports {DIN[9]}]
#set_property PACKAGE_PIN E16 [get_ports {DIN[8]}]
#set_property PACKAGE_PIN AF23 [get_ports {DIN[7]}]
#set_property PACKAGE_PIN AE23 [get_ports {DIN[6]}]
#set_property PACKAGE_PIN P25 [get_ports {DIN[5]}]
#set_property PACKAGE_PIN R25 [get_ports {DIN[4]}]
#set_property PACKAGE_PIN L24 [get_ports {DIN[3]}]
#set_property PACKAGE_PIN M24 [get_ports {DIN[2]}]
#set_property PACKAGE_PIN T25 [get_ports {DIN[1]}]
#set_property PACKAGE_PIN T24 [get_ports {DIN[0]}]
#set_property IOSTANDARD LVCMOS33 [get_ports "DIN*"]

# FREEZE_B connected to DOUT[0]
set_property PACKAGE_PIN AD21 [get_ports FREEZE_B]
set_property IOSTANDARD LVCMOS33 [get_ports FREEZE_B]
#set_property DRIVE 16 [get_ports FREEZE_B]
#set_property SLEW FAST [get_ports FREEZE_B]
set_property PULLDOWN true [get_ports FREEZE_B]
#set_property PACKAGE_PIN AD21 [get_ports {DOUT[0]}]

# FREEZE_A connected to DOUT[1]
set_property PACKAGE_PIN AE21 [get_ports FREEZE_A]
set_property IOSTANDARD LVCMOS33 [get_ports FREEZE_A]
#set_property DRIVE 16 [get_ports FREEZE_A]
#set_property SLEW FAST [get_ports FREEZE_A]
set_property PULLDOWN true [get_ports FREEZE_A]
#set_property PACKAGE_PIN AE21 [get_ports {DOUT[1]}]

# READ_B connected to DOUT[2]
set_property PACKAGE_PIN N26 [get_ports READ_B]
set_property IOSTANDARD LVCMOS33 [get_ports READ_B]
#set_property DRIVE 16 [get_ports READ_B]
#set_property SLEW FAST [get_ports READ_B]
set_property PULLDOWN true [get_ports READ_B]
#set_property PACKAGE_PIN N26 [get_ports {DOUT[2]}]


# READ_A connected to DOUT[3]
set_property PACKAGE_PIN M26 [get_ports READ_A]
set_property IOSTANDARD LVCMOS33 [get_ports READ_A]
#set_property DRIVE 16 [get_ports READ_A]
#set_property SLEW FAST [get_ports READ_A]
set_property PULLDOWN true [get_ports READ_A]
#set_property PACKAGE_PIN M26 [get_ports {DOUT[3]}]


# RESET_BCID connected to DOUT[4]
set_property PACKAGE_PIN U24 [get_ports RESET_BCID]
set_property IOSTANDARD LVCMOS33 [get_ports RESET_BCID]
set_property PULLDOWN true [get_ports RESET_BCID]
#set_property PACKAGE_PIN U24 [get_ports {DOUT[4]}]


# CLK_OUT connected to DOUT[5]
set_property PACKAGE_PIN U25 [get_ports CLK_OUT]
set_property IOSTANDARD LVCMOS33 [get_ports CLK_OUT]
set_property PULLDOWN true [get_ports CLK_OUT]
set_property DRIVE 16 [get_ports CLK_OUT]
set_property SLEW FAST [get_ports CLK_OUT]
#set_property PACKAGE_PIN U25 [get_ports {DOUT[5]}]


# CLK_BX connected to DOUT[6]
set_property PACKAGE_PIN W23 [get_ports CLK_BX]
set_property IOSTANDARD LVCMOS33 [get_ports CLK_BX]
set_property PULLDOWN true [get_ports CLK_BX]
set_property DRIVE 16 [get_ports CLK_BX]
set_property SLEW FAST [get_ports CLK_BX]
#set_property PACKAGE_PIN W23 [get_ports {DOUT[6]}]

# RST_N connected to DOUT[7]
set_property PACKAGE_PIN W24 [get_ports RST_N]
set_property IOSTANDARD LVCMOS33 [get_ports RST_N]
set_property PULLDOWN true [get_ports RST_N]
#set_property PACKAGE_PIN W24 [get_ports {DOUT[7]}]

# SI_CONF connected to DOUT[8]
set_property PACKAGE_PIN AB22 [get_ports SI_CONF]
set_property IOSTANDARD LVCMOS33 [get_ports SI_CONF]
set_property PULLDOWN true [get_ports SI_CONF]
#set_property PACKAGE_PIN AB22 [get_ports {DOUT[8]}]

# LD_CONF connected to DOUT[9]
set_property PACKAGE_PIN AC22 [get_ports LD_CONF]
set_property IOSTANDARD LVCMOS33 [get_ports LD_CONF]
#set_property DRIVE 16 [get_ports LD_CONF]
#set_property SLEW FAST [get_ports LD_CONF]
set_property PULLDOWN true [get_ports LD_CONF]
#set_property PACKAGE_PIN AC22 [get_ports {DOUT[9]}]

# CLK_CONF connected to DOUT[10]
set_property PACKAGE_PIN W20 [get_ports CLK_CONF]
set_property IOSTANDARD LVCMOS33 [get_ports CLK_CONF]
set_property PULLDOWN true [get_ports CLK_CONF]
set_property DRIVE 16 [get_ports CLK_CONF]
set_property SLEW FAST [get_ports CLK_CONF]
#set_property PACKAGE_PIN W20 [get_ports {DOUT[10]}]

# DEF_CONF connected to DOUT[11]
set_property PACKAGE_PIN Y21 [get_ports DEF_CONF]
set_property IOSTANDARD LVCMOS33 [get_ports DEF_CONF]
set_property PULLUP true [get_ports DEF_CONF]
#set_property PACKAGE_PIN Y21 [get_ports {DOUT[11]}]

# INJECTION connected to DOUT[12]
set_property PACKAGE_PIN N21 [get_ports INJECTION]
set_property IOSTANDARD LVCMOS33 [get_ports INJECTION]
set_property PULLDOWN true [get_ports INJECTION]
#set_property PACKAGE_PIN N21 [get_ports {DOUT[12]}]

# SO_CONF connected to DIN[0]
set_property PACKAGE_PIN T24 [get_ports SO_CONF]
set_property IOSTANDARD LVCMOS33 [get_ports SO_CONF]
#set_property PACKAGE_PIN T24 [get_ports {DIN[0]}]

# HITOR_A connected to DIN[1]
set_property PACKAGE_PIN T25 [get_ports HITOR_A]
set_property IOSTANDARD LVCMOS33 [get_ports HITOR_A]
#set_property PACKAGE_PIN T25 [get_ports {DIN[1]}]

# HITOR_B connected to DIN[2]
set_property PACKAGE_PIN M24 [get_ports HITOR_B]
set_property IOSTANDARD LVCMOS33 [get_ports HITOR_B]
#set_property PACKAGE_PIN M24 [get_ports {DIN[2]}]

# OUT_A connected to DIN[3]
set_property PACKAGE_PIN L24 [get_ports OUT_A]
set_property IOSTANDARD LVCMOS33 [get_ports OUT_A]
#set_property PACKAGE_PIN L24 [get_ports {DIN[3]}]

# OUT_B connected to DIN[4]
set_property PACKAGE_PIN R25 [get_ports OUT_B]
set_property IOSTANDARD LVCMOS33 [get_ports OUT_B]
#set_property PACKAGE_PIN R25 [get_ports {DIN[4]}]

# TOK_A connected to DIN[5]
set_property PACKAGE_PIN P25 [get_ports TOK_A]
set_property IOSTANDARD LVCMOS33 [get_ports TOK_A]
#set_property PACKAGE_PIN P25 [get_ports {DIN[5]}]

# TOK_B connected to DIN[6]
set_property PACKAGE_PIN AE23 [get_ports TOK_B]
set_property IOSTANDARD LVCMOS33 [get_ports TOK_B]
#set_property PACKAGE_PIN AE23 [get_ports {DIN[6]}]

# INJECTION connected to INJ_STRB
#set_property PACKAGE_PIN F20 [get_ports INJECTION]
#set_property IOSTANDARD LVCMOS33 [get_ports INJECTION]

set_property PACKAGE_PIN V21 [get_ports RJ45_TRIGGER]
set_property PACKAGE_PIN Y25 [get_ports RJ45_RESET]
set_property IOSTANDARD LVCMOS33 [get_ports RJ45_RESET]
set_property IOSTANDARD LVCMOS33 [get_ports RJ45_TRIGGER]




