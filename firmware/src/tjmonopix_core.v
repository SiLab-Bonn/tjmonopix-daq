
`timescale 1ns / 1ps
`default_nettype none

module tjmonopix_core (
    
    //local bus
    input wire BUS_CLK,
    inout wire [7:0] BUS_DATA,
    input wire [15:0] BUS_ADD,
    input wire BUS_RD,
    input wire BUS_WR,
    input wire BUS_RST,

    //clocks
    input wire CLK8,
    input wire CLK40,
    input wire CLK16,
    input wire CLK160,
    input wire CLK320,
    
    //fifo
    input wire ARB_READY_OUT,
    output wire ARB_WRITE_OUT,
    output wire [31:0] ARB_DATA_OUT,
    input wire FIFO_FULL,
    input wire FIFO_NEAR_FULL,

    //LED
    output wire [4:0] LED,
    
    input wire [2:0] LEMO_RX,
    output wire [2:0] LEMO_TX, // TX[0] == RJ45 trigger clock output, TX[1] == RJ45 busy output
    input wire RJ45_RESET,
    input wire RJ45_TRIGGER,

    input wire SO_CONF,
    output wire CLK_CONF,
    output wire DEF_CONF,
    output wire SI_CONF,
    output wire LD_CONF,
    output wire RST_N,
    
    output wire INJECTION,
	output wire INJECTION_MON,
    
    output wire CLK_BX,
    output wire CLK_OUT,
    output wire READ_A,
    output wire READ_B,
    output wire FREEZE_A,
    output wire FREEZE_B,
    output wire RESET_BCID,
  
    input wire TOK_A,
    input wire TOK_B,
    input wire OUT_A,
    input wire OUT_B,
    input wire HITOR_A, 
    input wire HITOR_B
 
);

// -------  MODULE ADREESSES  ------- //
localparam GPIO_BASEADDR = 16'h0000;
localparam GPIO_HIGHADDR = 16'h0100-1;

localparam PULSE_INJ_BASEADDR = 16'h0100;
localparam PULSE_INJ_HIGHADDR = 16'h0200-1;

localparam DATA_RX_BASEADDR = 16'h0500;
localparam DATA_RX_HIGHADDR = 16'h0600-1;

localparam SPI_BASEADDR = 16'h1000;
localparam SPI_HIGHADDR = 16'h2000-1;

localparam PULSE_GATE_TDC_BASEADDR = 16'h0400;
localparam PULSE_GATE_TDC_HIGHADDR = 16'h0500-1;

localparam TLU_BASEADDR = 16'h0600;
localparam TLU_HIGHADDR = 16'h0700-1;

localparam TS_BASEADDR = 16'h0700;
localparam TS_HIGHADDR = 16'h0800-1;

localparam FIFO_BASEADDR = 16'h8000;
localparam FIFO_HIGHADDR = 16'h9000-1;

localparam TS_TDC_BASEADDR = 16'h0900;
localparam TS_TDC_HIGHADDR = 16'h0A00-1;

localparam TS_TLU_BASEADDR = 16'h0A00;
localparam TS_TLU_HIGHADDR = 16'h0B00-1;


// -------  USER MODULES  ------- //
wire [15:0] GPIO_OUT;
gpio 
#( 
    .BASEADDR(GPIO_BASEADDR), 
    .HIGHADDR(GPIO_HIGHADDR),
    .IO_WIDTH(16),
    .IO_DIRECTION(16'hffff)
) gpio
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .IO(GPIO_OUT)
    );    

wire RESET_CONF, RESET_BCID_CONF;
wire EN_BX_CLK_CONF, EN_OUT_CLK_CONF, SELECTAB;
wire READ_AB, FREEZE_AB, OUT_AB, TOK_AB;
wire EN_HITOR_TX;

assign RESET_CONF = GPIO_OUT[0];
assign RESET_BCID_CONF = GPIO_OUT[1];
assign EN_BX_CLK_CONF = GPIO_OUT[2];
assign EN_OUT_CLK_CONF = GPIO_OUT[3];
assign DEF_CONF = ~GPIO_OUT[4];
assign SELECTAB = GPIO_OUT[5];
assign EN_HITOR_TX = GPIO_OUT[5];

wire CONF_CLK;
assign CONF_CLK = CLK8;
    
wire SCLK, SDI, SDO, SEN, SLD;
spi 
#( 
    .BASEADDR(SPI_BASEADDR), 
    .HIGHADDR(SPI_HIGHADDR),
    .MEM_BYTES(4096) 
    )  spi_conf
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .SPI_CLK(CONF_CLK),

    .SCLK(SCLK),
    .SDI(SDI),
    .SDO(SDO),
    .SEN(SEN),
    .SLD(SLD)
);

assign CLK_CONF = SCLK;
assign SI_CONF = SDI;
assign SDO = SO_CONF;    
assign LD_CONF = SLD;

wire GATE_TDC;
    
pulse_gen
#( 
    .BASEADDR(PULSE_INJ_BASEADDR), 
    .HIGHADDR(PULSE_INJ_HIGHADDR)
) pulse_gen_inj
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK(CLK40), //~CLK40),
    .EXT_START(GATE_TDC),
    .PULSE(INJECTION)
);

pulse_gen
#( 
    .BASEADDR(PULSE_GATE_TDC_BASEADDR), 
    .HIGHADDR(PULSE_GATE_TDC_HIGHADDR)
    ) pulse_gen_gate_tdc
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK(CLK40),
    .EXT_START(1'b0),
    .PULSE(GATE_TDC) 
);    

wire FE_FIFO_READ, TS_FIFO_READ, TLU_FIFO_READ, TS_TDC_FIFO_READ,TS_TLU_FIFO_READ;
wire FE_FIFO_EMPTY, TS_FIFO_EMPTY, TLU_FIFO_EMPTY,TS_TDC_FIFO_EMPTY,TS_TLU_FIFO_EMPTY;
wire [31:0] FE_FIFO_DATA;
wire [31:0] TS_FIFO_DATA;
wire [31:0] TLU_FIFO_DATA;
wire [31:0] TS_TDC_FIFO_DATA;
wire [31:0] TS_TLU_FIFO_DATA;
wire TLU_FIFO_PEEMPT_REQ;


rrp_arbiter 
#( 
    .WIDTH(5)
) rrp_arbiter (

    .RST(BUS_RST),
    .CLK(BUS_CLK),

    .WRITE_REQ({~TS_TDC_FIFO_EMPTY,~TS_TLU_FIFO_EMPTY, ~TS_FIFO_EMPTY, ~FE_FIFO_EMPTY, ~TLU_FIFO_EMPTY}),
    .HOLD_REQ({4'b0, TLU_FIFO_PEEMPT_REQ}),
    .DATA_IN({TS_TDC_FIFO_DATA,TS_TLU_FIFO_DATA,TS_FIFO_DATA,FE_FIFO_DATA, TLU_FIFO_DATA}),
    .READ_GRANT({TS_TDC_FIFO_READ,TS_TLU_FIFO_READ,TS_FIFO_READ,FE_FIFO_READ, TLU_FIFO_READ}),

    .READY_OUT(ARB_READY_OUT),
    .WRITE_OUT(ARB_WRITE_OUT),
    .DATA_OUT(ARB_DATA_OUT)
);

wire TDC_TDC_OUT, TDC_TRIG_OUT;
wire HITOR_AB;

wire [64:0] TIMESTAMP;
wire TLU_BUSY,TLU_CLOCK;
wire TRIGGER_ACKNOWLEDGE_FLAG,TRIGGER_ACCEPTED_FLAG;

//assign HITOR_AB = (SELECTAB)? HITOR_B : HITOR_A;

//// TLU

tlu_controller #(
    .BASEADDR(TLU_BASEADDR),
    .HIGHADDR(TLU_HIGHADDR),
    .DIVISOR(8),
    .TIMESTAMP_N_OF_BIT(64)
) i_tlu_controller (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    
    .TRIGGER_CLK(CLK40),
    
    .FIFO_READ(TLU_FIFO_READ),
    .FIFO_EMPTY(TLU_FIFO_EMPTY),
    .FIFO_DATA(TLU_FIFO_DATA),
    
    .FIFO_PREEMPT_REQ(TLU_FIFO_PEEMPT_REQ),
    
    .TRIGGER({7'b0,TDC_TRIG_OUT}),
    .TRIGGER_VETO({7'b0,FIFO_FULL}),
	 
    .TRIGGER_ACKNOWLEDGE(TRIGGER_ACKNOWLEDGE_FLAG),
    .TRIGGER_ACCEPTED_FLAG(TRIGGER_ACCEPTED_FLAG),
	 //.EXT_TRIGGER_ENABLE(TLU_EXT_TRIGGER_ENABLE)
	 
    .TLU_TRIGGER(RJ45_TRIGGER),
    .TLU_RESET(RJ45_RESET),
    .TLU_BUSY(TLU_BUSY),
    .TLU_CLOCK(TLU_CLOCK),
    
    .TIMESTAMP(TIMESTAMP)
);
assign TRIGGER_ACKNOWLEDGE_FLAG = TRIGGER_ACCEPTED_FLAG;

timestamp
#(
    .BASEADDR(TS_BASEADDR),
    .HIGHADDR(TS_HIGHADDR),
    .IDENTIFIER(4'b0101)
)i_timestamp(
    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RST(BUS_RST),
    .BUS_WR(BUS_WR),
    .BUS_RD(BUS_RD),
    
    .CLK(CLK40),
	 .DI(LEMO_RX[1]),
	 .EXT_ENABLE(GATE_TDC),
	 .EXT_TIMESTAMP(TIMESTAMP),

    .FIFO_READ(TS_FIFO_READ),
    .FIFO_EMPTY(TS_FIFO_EMPTY),
    .FIFO_DATA(TS_FIFO_DATA)
    
);

timestamp_div
#(
    .BASEADDR(TS_TDC_BASEADDR),
    .HIGHADDR(TS_TDC_HIGHADDR),
    .IDENTIFIER(4'b0110)
)i_timestamp_div_tdc(
    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RST(BUS_RST),
    .BUS_WR(BUS_WR),
    .BUS_RD(BUS_RD),
    
    .CLK40(CLK40),
    .CLK160(CLK160),
    .CLK320(CLK320),
	 .DI(HITOR_B),
	 //.DI(LEMO_RX[1]),
	 .EXT_ENABLE(GATE_TDC),
	 .EXT_TIMESTAMP(TIMESTAMP),

    .FIFO_READ(TS_TDC_FIFO_READ),
    .FIFO_EMPTY(TS_TDC_FIFO_EMPTY),
    .FIFO_DATA(TS_TDC_FIFO_DATA)
    
);

timestamp_div
#(
    .BASEADDR(TS_TLU_BASEADDR),
    .HIGHADDR(TS_TLU_HIGHADDR),
    .IDENTIFIER(4'b0111)
)i_timestamp_div_tlu(
    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RST(BUS_RST),
    .BUS_WR(BUS_WR),
    .BUS_RD(BUS_RD),
    
    .CLK40(CLK40),
    .CLK160(CLK160),
    .CLK320(CLK320),
    .DI(RJ45_TRIGGER),
	 .EXT_ENABLE(~TLU_BUSY),
	 .EXT_TIMESTAMP(TIMESTAMP),

    .FIFO_READ(TS_TLU_FIFO_READ),
    .FIFO_EMPTY(TS_TLU_FIFO_EMPTY),
    .FIFO_DATA(TS_TLU_FIFO_DATA)
);

tjmono_data_rx #(
   .BASEADDR(DATA_RX_BASEADDR),
   .HIGHADDR(DATA_RX_HIGHADDR),
   .IDENTYFIER(2'b00)
) tjmono_data_rx (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    
    .CLK_BX(CLK40),
    .RX_TOKEN(TOK_AB), 
    .RX_DATA(OUT_AB),
    .RX_CLK(CLK40),
    .RX_READ(READ_AB), 
    .RX_FREEZE(FREEZE_AB), 
    .TIMESTAMP(TIMESTAMP),
    
    .FIFO_READ(FE_FIFO_READ),
    .FIFO_EMPTY(FE_FIFO_EMPTY),
    .FIFO_DATA(FE_FIFO_DATA),
    
    .LOST_ERROR()
    
);

assign OUT_AB = (SELECTAB)? OUT_B : OUT_A;
assign TOK_AB = (SELECTAB)? TOK_B : TOK_A;
assign READ_A = (SELECTAB)? 1'b0 : READ_AB;
assign FREEZE_A = (SELECTAB)? 1'b0 : FREEZE_AB;
assign READ_B = (SELECTAB)? READ_AB : 1'b0;
assign FREEZE_B = (SELECTAB)? FREEZE_AB : 1'b0;

ODDR clk_bx_gate(.D1(EN_BX_CLK_CONF), .D2(1'b0), .C(CLK40), .CE(1'b1), .R(1'b0), .S(1'b0), .Q(CLK_BX) );
assign CLK_OUT = EN_OUT_CLK_CONF ? CLK40 : 1'b0;

reg nRST_reg;
assign RST_N = nRST_reg;
always@(negedge CLK40)
    nRST_reg <= !RESET_CONF;
   
reg RST_BCID_reg;
assign RESET_BCID = RST_BCID_reg;
always@(negedge CLK40)
    RST_BCID_reg <= RESET_BCID_CONF;


// LED assignments
assign LED[0] = 0;
assign LED[1] = 0;
assign LED[2] = 0;
assign LED[3] = 0;
assign LED[4] = 0;

assign LEMO_TX[0] = TLU_CLOCK; // trigger clock; also connected to RJ45 output
assign LEMO_TX[1] = TLU_BUSY;  // TLU_BUSY signal; also connected to RJ45 output. Asserted when TLU FSM has 
assign LEMO_TX[2] = INJECTION;

//assign INJECTION_MON = INJECTION;
endmodule
