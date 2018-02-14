//Verilog HDL for "TJ_Monopix_01", "MONOPIX_TOP" "functional"

//`include "../sim/mono_pixel.sv"

`timescale 1ns / 1ps

// synopsys translate_off
module mono_pixel 
//#(
//    parameter ADDR = 0
//)(
    (
    input [8:0] ADDR,
    input ANA_HIT,
    input Injection,
        
    output logic OUT_MONITOR,
    
    input logic nRST, TOK_IN, READ, FREEZE,
    input logic [5:0] Time,
    
    output logic TOK_OUT,
    inout logic [5:0] LE_RAM, TE_RAM, 
    inout logic [8:0] ROW_SW,
    
    input logic injection_en, preamp_en, monitor_en

);

logic HIT;
assign HIT = ((ANA_HIT | (Injection & injection_en)) & preamp_en);

assign OUT_MONITOR = HIT & monitor_en;

// ------ DIGITAL ---------
reg latched_TE;
wire RstInt;
always@(negedge HIT or posedge RstInt)
    if(RstInt)
        latched_TE <= 0;
    else
        latched_TE <= 1;

reg HIT_FLAG;
always@(*)
    if(RstInt)
        HIT_FLAG = 0;
    else if(latched_TE & FREEZE==0)  
        HIT_FLAG = 1;

wire ReadPix;        
assign TOK_OUT = TOK_IN | HIT_FLAG;
assign ReadPix = (TOK_IN==0 & HIT_FLAG==1);

reg ReadLatch;
always@(*)
    if(!READ)
        ReadLatch = ReadPix;

logic READ_INT;
assign  #1 READ_INT = ReadLatch & READ;
assign RstInt = (nRST == 0 | READ_INT==1);
 

reg [5:0] LeTime, TeTime;
always@(posedge HIT)
    LeTime <= Time;
    
always@(negedge HIT)
    TeTime <= Time;

assign LE_RAM = READ_INT ? LeTime : 6'bz;
assign TE_RAM = READ_INT ? TeTime : 6'bz;
assign ROW_SW = READ_INT ? ADDR[8:0] : 9'bz; 
    
endmodule

// synopsys translate_on

module MONOPIX_TOP ( DIG_MON_COMP, DIG_MON_HV, DIG_MON_PMOS, DIG_MON_PMOS_NOSF,
Data_COMP, Data_HV, Data_PMOS, Data_PMOS_NOSF, nTOK_COMP, nTOK_HV, nTOK_PMOS,
nTOK_PMOS_NOSF, BiasSF_PAD, DACMON_IBIAS_PAD, DACMON_ICASN_PAD, DACMON_IDB_PAD,
DACMON_IRESET_PAD, DACMON_ITHR_PAD, DACMON_VCASN_DAC_PAD, DACMON_VH_PAD, DACMON_VL_PAD,
DACMON_VRESET_P_PAD, GNDA, GNDA_DAC, GNDD, HV_DIODE, OUTA_MON_L_PAD, OUTA_MON_R_PAD,
PSUB, PWELL, VCASN_DAC_MON_L_PAD, VCASN_DAC_MON_R_PAD, VCASN_MON_L_PAD, VCASN_MON_R_PAD,
VDDA, VDDA_DAC, VDDD, VPCNOSF, VPC_PAD, BcidMtx, DIG_MON_SEL, FREEZE_COMP,
FREEZE_HV, FREEZE_PMOS, FREEZE_PMOS_NOSF, INJ_IN, INJ_IN_MON_L, INJ_IN_MON_R,
INJ_ROW, MASKD, MASKH, MASKV, Read_COMP, Read_HV, Read_PMOS, Read_PMOS_NOSF,
SET_IBIAS, SET_IBUFN_L, SET_IBUFN_R, SET_IBUFP_L, SET_IBUFP_R, SET_ICASN, SET_IDB,
SET_IRESET, SET_IRESET_BIT, SET_ITHR, SET_VCASN, SET_VCLIP, SET_VH, SET_VL,
SET_VRESET_D, SET_VRESET_P, SWCNTL_DACMONI, SWCNTL_DACMONV, SWCNTL_IBIAS, SWCNTL_ICASN,
SWCNTL_IDB, SWCNTL_IREF, SWCNTL_IRESET, SWCNTL_ITHR, SWCNTL_VCASN, SWCNTL_VCLIP,
SWCNTL_VH, SWCNTL_VL, SWCNTL_VRESET_D, SWCNTL_VRESET_P, nRST );

//POWER
  inout VDDA;
  inout VDDA_DAC;
  inout VDDD;
  //inout VDDP;
  inout HV_DIODE;

  inout GNDA;
  inout GNDA_DAC;
  inout GNDD;
  //inout GNDP;
  inout PSUB;
  inout PWELL;

//Analog
  inout BiasSF_PAD;
  inout VPC_PAD;
  inout VPCNOSF;

  //Analog out
  inout  [3:0] OUTA_MON_L_PAD;
  inout  [3:0] OUTA_MON_R_PAD;
  inout VCASN_DAC_MON_L_PAD;
  inout VCASN_DAC_MON_R_PAD;
  inout VCASN_MON_L_PAD;
  inout VCASN_MON_R_PAD;

  //Analog in-out (override/monitor)
  inout DACMON_IBIAS_PAD;
  inout DACMON_IDB_PAD;
  inout DACMON_ITHR_PAD;
  inout DACMON_IRESET_PAD;
  inout DACMON_ICASN_PAD;

  inout DACMON_VRESET_P_PAD;
  inout DACMON_VL_PAD;
  inout DACMON_VH_PAD;
  inout DACMON_VCASN_DAC_PAD;

//Digital Input
  //Configuration DAC
  input  [127:0] SET_VRESET_P;
  input  [127:0] SET_VH;
  input  [127:0] SET_VL;
  input  [127:0] SET_VCASN;
  input  [127:0] SET_VRESET_D;
  input  [127:0] SET_VCLIP;

  input  [127:0] SET_IBIAS;
  input  [127:0] SET_IDB;
  input  [127:0] SET_ITHR;
  input  [127:0] SET_IRESET;
  input  [127:0] SET_ICASN;

  input  [3:0] SET_IBUFN_L;
  input  [3:0] SET_IBUFN_R;
  input  [3:0] SET_IBUFP_L;
  input  [3:0] SET_IBUFP_R;

  input SET_IRESET_BIT;

  input SWCNTL_DACMONI;
  input SWCNTL_DACMONV;
  input SWCNTL_IBIAS;
  input SWCNTL_ICASN;
  input SWCNTL_IDB;
  input SWCNTL_IREF;
  input SWCNTL_IRESET;
  input SWCNTL_ITHR;
  input SWCNTL_VCASN;
  input SWCNTL_VCLIP;
  input SWCNTL_VH;
  input SWCNTL_VL;
  input SWCNTL_VRESET_D;
  input SWCNTL_VRESET_P;

  //Configuration Matrix
  input  [447:0] MASKV;
  input  [223:0] MASKH;
  input  [447:0] MASKD;

  input  [223:0] INJ_ROW;
  input  [447:0] DIG_MON_SEL;

  //Pulsing
  input  [447:0] INJ_IN;
  input INJ_IN_MON_L;
  input INJ_IN_MON_R;

  //Readout
  input  [223:0] nRST;
  input  [1343:0] BcidMtx;
  input  [55:0] Read_PMOS_NOSF;
  input  [55:0] Read_PMOS;
  input  [55:0] Read_COMP;
  input  [55:0] Read_HV;
  input  [55:0] FREEZE_PMOS_NOSF;
  input  [55:0] FREEZE_PMOS;
  input  [55:0] FREEZE_COMP;
  input  [55:0] FREEZE_HV;

//Digital Output
  //HITOR
  output  [111:0] DIG_MON_PMOS_NOSF;
  output  [111:0] DIG_MON_PMOS;
  output  [111:0] DIG_MON_COMP;
  output  [111:0] DIG_MON_HV;

  //Readout
  output  [55:0] nTOK_PMOS_NOSF;
  output  [55:0] nTOK_PMOS;
  output  [55:0] nTOK_COMP;
  output  [55:0] nTOK_HV;
  output  [1175:0] Data_PMOS_NOSF;
  output  [1175:0] Data_PMOS;
  output  [1175:0] Data_COMP;
  output  [1175:0] Data_HV;
  
  // synopsys translate_off
  
  wire [448*224-1:0] ANA_HIT;
  logic [4*56-1:0] READ;
  assign READ = {Read_HV, Read_COMP, Read_PMOS, Read_PMOS_NOSF};

  logic [4*56-1:0] FREEZE;
  assign FREEZE = {FREEZE_HV, FREEZE_COMP, FREEZE_PMOS, FREEZE_PMOS_NOSF};
  
  logic [4*56-1:0][5:0] Time;
  assign Time = BcidMtx;
  
  logic [4*56-1:0] token;
  assign  {nTOK_HV, nTOK_COMP, nTOK_PMOS, nTOK_PMOS_NOSF} = ~token;
  
  wire [4*56-1:0][5:0] LE;
  wire [4*56-1:0][5:0] TE;
  wire [4*56-1:0][8:0] ADDR;
  
  logic [4*56-1:0][20:0] data;
  assign  {Data_HV, Data_COMP, Data_PMOS, Data_PMOS_NOSF} = data;
  
  wire [2*4*56-1:0] monitor;
  assign  {DIG_MON_HV, DIG_MON_COMP, DIG_MON_PMOS, DIG_MON_PMOS_NOSF} = monitor & DIG_MON_SEL;
  

`ifndef TEST_DC
    `define TEST_DC 224
`endif
    generate
        genvar col_i;
        genvar row_i;
        for (col_i=0; col_i<224; col_i=col_i+1) begin: col_gen
            wire [448:0] tok_int;
            wire [1:0][223:0] monitor_int;
            
            assign tok_int[0] = 0;
            assign monitor[2*col_i] = |monitor_int[0][col_i];
            assign monitor[2*col_i+1] = |monitor_int[1][col_i];
            
            if ( col_i < `TEST_DC ) begin
                assign token[col_i] = tok_int[448];
                always@(negedge READ[col_i])
                    data[col_i] <= {TE[col_i], LE[col_i], ADDR[col_i]};
                
                for (row_i = 0; row_i <448; row_i = row_i + 1) begin: row_gen
                  logic [8:0] ADDRrow;
                  logic [8:0] ADDRmap;
                  assign ADDRrow = (ADDRmap > 223) ? (ADDRmap+32) : ADDRmap;
                  assign ADDRmap = ((!(row_i % 2))*(row_i/2))+((row_i % 2)*(row_i+223-((row_i-1)/2)));
                  mono_pixel pix
                  //mono_pixel #(.ADDR(row_i)) pix
                  //mono_pixel #(.ADDR(((!(row_i % 2))*(row_i/2))+((row_i % 2)*(row_i+223-((row_i-1)/2))))) pix
                    (
                        .ADDR(ADDRrow),
                        .ANA_HIT(ANA_HIT[col_i*448+row_i]),
                        .Injection(INJ_IN[2*col_i + (row_i % 2)]),
                        .OUT_MONITOR(monitor_int[(row_i % 2)][row_i/2]),
                        
                        .nRST(nRST[col_i]),
                        .TOK_IN(tok_int[row_i]),
                        .READ(READ[col_i]),
                        .FREEZE(FREEZE[col_i]),
                        .Time(Time[col_i]),
                        
                        .TOK_OUT(tok_int[row_i+1]),
                        
                        .LE_RAM(LE[col_i]),
                        .TE_RAM(TE[col_i]),
                        .ROW_SW(ADDR[col_i]),
                        
                        .injection_en(INJ_ROW[row_i/2]),
                        .preamp_en(MASKH[col_i] | MASKV[row_i]), // MASKD
                        .monitor_en(1'b1) //?
                    );
                end
            end
            else begin
                assign token[col_i] = 0;
            end

             
            
        end
    endgenerate
 
        
    // synopsys translate_on

endmodule
