/**
 * ------------------------------------------------------------
 * Copyright (c) SILAB , Physics Institute of Bonn University 
 * ------------------------------------------------------------
 */

`timescale 1ps / 1ps


`include "firmware/src/tjmonopix_mio.v"
`include "MONOPIX.sv"
 
module tb (
    input wire FCLK_IN, 

    //full speed 
    inout wire [7:0] BUS_DATA,
    input wire [15:0] ADD,
    input wire RD_B,
    input wire WR_B,
    
    //high speed
    inout wire [7:0] FD,
    input wire FREAD,
    input wire FSTROBE,
    input wire FMODE
);

wire [19:0] SRAM_A;
wire [15:0] SRAM_IO;
wire SRAM_BHE_B;
wire SRAM_BLE_B;
wire SRAM_CE1_B;
wire SRAM_OE_B;
wire SRAM_WE_B;

wire [2:0] LEMO_RX;
assign LEMO_RX = 0;

wire DEF_CONF, SO_CONF, CLK_CONF, SI_CONF, LD_CONF, RST_N, RESET_BCID;
wire CLK_BX, CLK_OUT, INJECTION;

wire READ_A, READ_B, FREEZE_A, FREEZE_B, TOK_A, TOK_B, OUT_A, OUT_B;

tjmonopix_mio fpga (
    .FCLK_IN(FCLK_IN),
        
    .BUS_DATA(BUS_DATA), 
    .ADD(ADD), 
    .RD_B(RD_B), 
    .WR_B(WR_B), 
    .FDATA(FD), 
    .FREAD(FREAD), 
    .FSTROBE(FSTROBE), 
    .FMODE(FMODE),

    .SRAM_A(SRAM_A), 
    .SRAM_IO(SRAM_IO), 
    .SRAM_BHE_B(SRAM_BHE_B), 
    .SRAM_BLE_B(SRAM_BLE_B), 
    .SRAM_CE1_B(SRAM_CE1_B), 
    .SRAM_OE_B(SRAM_OE_B), 
    .SRAM_WE_B(SRAM_WE_B),
    
    
    .LEMO_RX(LEMO_RX),
    
    .SO_CONF(SO_CONF),
    .CLK_CONF(CLK_CONF),
    .DEF_CONF(DEF_CONF),
    .SI_CONF(SI_CONF),
    .LD_CONF(LD_CONF),
    .RST_N(RST_N),
    
    .INJECTION(INJECTION),
    
    .CLK_BX(CLK_BX),
    .CLK_OUT(CLK_OUT),
    .READ_A(READ_A),
    .READ_B(READ_B),
    .FREEZE_A(FREEZE_A),
    .FREEZE_B(FREEZE_B),
    .RESET_BCID(RESET_BCID),
  
    .TOK_A(TOK_A),
    .TOK_B(TOK_B),
    .OUT_A(OUT_A),
	.OUT_B(OUT_B),
    .HITOR_A(), 
    .HITOR_B()
    
);   

//SRAM Model
reg [15:0] sram [1048576-1:0];
assign SRAM_IO = !SRAM_OE_B ? sram[SRAM_A] : 16'hzzzz;
always@(negedge SRAM_WE_B)
    sram[SRAM_A] <= SRAM_IO;

wire INJ_PULSE;
assign INJ_PULSE = INJECTION;

logic [224:0][447:0] ana_hit;
assign dut.MONOPIX_TOP.ANA_HIT = ana_hit;
assign ana_hit = 0;

 MONOPIX dut (
        .DEF_CONF_PAD(DEF_CONF),
        .CLK_CONF_PAD(CLK_CONF),
        .LD_CONF_PAD(LD_CONF),
        .SI_CONF_PAD(SI_CONF),
        .SO_CONF_PAD(SO_CONF),
        
        .RST_N_PAD(RST_N),
        .CLK_BX_PAD(CLK_BX), 
        .CLK_OUT_PAD(CLK_OUT),
        .RESET_BCID_PAD(RESET_BCID),
        
        .READ_PMOS_NOSF_PAD(READ_A), .READ_PMOS_PAD(1'b0), .READ_COMP_PAD(1'b0), .READ_HV_PAD(1'b0),
        .FREEZE_PMOS_NOSF_PAD(FREEZE_A), .FREEZE_PMOS_PAD(1'b0), .FREEZE_COMP_PAD(1'b0), .FREEZE_HV_PAD(1'b0),
        
        .TOKEN_PMOS_NOSF_PAD(TOK_A), .TOKEN_PMOS_PAD(), .TOKEN_COMP_PAD(), .TOKEN_HV_PAD(), 
        .OUT_PMOS_NOSF_PAD(OUT_A), .OUT_PMOS_PAD(), .OUT_COMP_PAD(), .OUT_HV_PAD(),
        
        .PULSE_PAD(INJ_PULSE)
    
        
    );
    
initial begin
    $dumpfile("/tmp/tjmonopix.vcd.gz");
    $dumpvars(0);
end

endmodule
