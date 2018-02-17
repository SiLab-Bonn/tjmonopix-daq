`default_nettype wire
`include "DIGITAL/defines.sv"
`include "DIGITAL/readout.sv"
`include "DIGITAL/cnfg_reg.v"
`include "MATRIX_DAC/MONOPIX_TOP.v"
`include "PADS/PAD_DVDD.v"
`include "PADS/PAD_DVSS.v"
`include "PADS/Pulldown_pol_IO_lowcap_EN.v"
`include "PADS/decoupling_cap_filler.v"

module MONOPIX(
    
    // digital
    input DEF_CONF_PAD, //IO Pulldown PAD
    input CLK_CONF_PAD, //IO Pulldown PAD
    input LD_CONF_PAD, //IO Pulldown PAD
    input SI_CONF_PAD, //IO Pulldown PAD
    output SO_CONF_PAD, //IO Pulldown PAD
    input RST_N_PAD, //IO Pulldown PAD
    input CLK_BX_PAD, //IO Pulldown PAD
    input CLK_OUT_PAD, //IO Pulldown PAD
    input RESET_BCID_PAD, //IO Pulldown PAD
    input READ_PMOS_NOSF_PAD, READ_PMOS_PAD, READ_COMP_PAD, READ_HV_PAD, //IO Pulldown PAD
    input FREEZE_PMOS_NOSF_PAD, FREEZE_PMOS_PAD, FREEZE_COMP_PAD, FREEZE_HV_PAD, //IO Pulldown PAD
    output TOKEN_PMOS_NOSF_PAD, TOKEN_PMOS_PAD, TOKEN_COMP_PAD, TOKEN_HV_PAD, //IO Pulldown PAD
    output OUT_PMOS_NOSF_PAD, OUT_PMOS_PAD, OUT_COMP_PAD, OUT_HV_PAD, //IO Pulldown PAD
    
    output TOKEN_PMOS_NOSF_N_PAD, TOKEN_PMOS_N_PAD, TOKEN_COMP_N_PAD, TOKEN_HV_N_PAD, //IO Pulldown PAD
    output OUT_PMOS_NOSF_N_PAD, OUT_PMOS_N_PAD, OUT_COMP_N_PAD, OUT_HV_N_PAD, //IO Pulldown PAD
    
   
    input PULSE_PAD, //IO Pulldown PAD
    output [3:0] HIT_OR_PAD, HIT_OR_N_PAD, //IO Pulldown PAD
    
    // Analog -> Analog Pads
    inout BiasSF_PAD,  // Analog Pad IBIAS
    inout VPC_PAD,     // Analog Pad ANALOG
    inout VPCNOSF, // Analog Pad NORES

    inout DACMON_IBIAS_PAD, // Analog PAD IANALOG
    inout DACMON_IDB_PAD,   // Analog PAD IANALOG
    inout DACMON_ITHR_PAD,  // Analog PAD IANALOG
    inout DACMON_IRESET_PAD, // Analog PAD IANALOG
    inout DACMON_ICASN_PAD,  // Analog PAD IANALOG

    inout DACMON_VRESET_P_PAD,  // Analog PAD IANALOG
    inout DACMON_VL_PAD,  // Analog PAD IANALOG
    inout DACMON_VH_PAD,  // Analog PAD IANALOG
    inout DACMON_VCASN_DAC_PAD,  // Analog PAD IANALOG
    
    inout [3:0]  OUTA_MON_L_PAD, //Analog PAD ANALOG
    inout [3:0]  OUTA_MON_R_PAD, //Analog PAD ANALOG
    inout VCASN_MON_L_PAD,       //Analog PAD ANALOG
    inout VCASN_DAC_MON_L_PAD,   //Analog PAD ANALOG
    inout VCASN_MON_R_PAD,       //Analog PAD ANALOG
    inout VCASN_DAC_MON_R_PAD,   //Analog PAD ANALOG

    // Power Nets
    inout       VDDA, // Analog Supply
    inout       GNDA, // Analog Ground

    inout       VDDD, // Digital Supply
    inout       GNDD, // Digital Ground
    
    // DAC power
    inout       VDDA_DAC, // DAC analog Supply
    inout       GNDA_DAC, // DAC Analog Ground

    //inout       VDDP,  // Periphery Digital Supply
    //inout       GNDP,  // Periphery Digital Ground
    
    inout       PSUB,   // Die PSUBstrate bias
    inout       PWELL,  // Die PSUBstrate bias under the pixel matrix
    
    inout       HV_DIODE
);

    //
    //   IO
    //
    
    //Configuration
    t_conf conf;
    wire DefConf, ClkConf, LdConf, SiConf, SoConf; 
        
    //Readout
    wire ClkBx, ClkOut;
    wire ResetBcid;
    wire ReadPMOS_NOSF, ReadPMOS, ReadCOMP, ReadHV;
    wire FreezePMOS_NOSF, FreezePMOS, FreezeCOMP, FreezeHV;
    wire OutPMOS_NOSF, OutPMOS, OutCOMP, OutHV;
    wire TokenPMOS_NOSF, TokenPMOS, TokenCOMP, TokenHV;
    
    wire nRST_EXT;
    wire [223:0] nRST;
    assign nRST = {224{nRST_EXT}};
    wire Pulse;
    
    logic [3:0] HitOr;

// SHIFT REGISTER CONFIGURATION
    Pulldown_pol_IO_lowcap_EN PAD_DEF_CONF ( .CIN(DefConf), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(DEF_CONF_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_CLK_CONF ( .CIN(ClkConf), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(CLK_CONF_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_LD_CONF ( .CIN(LdConf), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(LD_CONF_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) );    //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_SI_CONF ( .CIN(SiConf), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(SI_CONF_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) );    //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_SO_CONF ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(SO_CONF_PAD), .SUB(PSUB), .DOUT(SoConf), .OEN(1'b0) );    //TRANSMITTER (OEN=0 in the new PAD)

// CLK, RESET, PULSE 
    Pulldown_pol_IO_lowcap_EN PAD_RST_N ( .CIN(nRST_EXT), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(RST_N_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_CLK_BX ( .CIN(ClkBx), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(CLK_BX_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_CLK_OUT ( .CIN(ClkOut), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(CLK_OUT_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_RESET_BCID ( .CIN(ResetBcid), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(RESET_BCID_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_PULSE ( .CIN(Pulse), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(PULSE_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)

// FLAVOR 1 (PMOS_NOSF) I/O    
    Pulldown_pol_IO_lowcap_EN PAD_READ_PMOS_NOSF ( .CIN(ReadPMOS_NOSF), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(READ_PMOS_NOSF_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_FREEZE_PMOS_NOSF ( .CIN(FreezePMOS_NOSF), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(FREEZE_PMOS_NOSF_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_TOKEN_PMOS_NOSF ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_PMOS_NOSF_PAD), .SUB(PSUB), .DOUT(TokenPMOS_NOSF), .OEN(conf.EN_OUT[0]) ); //TRANSMITTER (Default=enabled=0)
    Pulldown_pol_IO_lowcap_EN PAD_OUT_PMOS_NOSF ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_PMOS_NOSF_PAD), .SUB(PSUB), .DOUT(OutPMOS_NOSF), .OEN(conf.EN_OUT[0]) ); //TRANSMITTER (Default=enabled=0)
//Diff PADS
    Pulldown_pol_IO_lowcap_EN PAD_nTOKEN_PMOS_NOSF ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_PMOS_NOSF_N_PAD), .SUB(PSUB), .DOUT(~TokenPMOS_NOSF), .OEN(conf.nEN_OUT[0]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_nOUT_PMOS_NOSF ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_PMOS_NOSF_N_PAD), .SUB(PSUB), .DOUT(~OutPMOS_NOSF), .OEN(conf.nEN_OUT[0]) ); //TRANSMITTER (Default=disabled=1)

// FLAVOR 2 (PMOS) I/O     
    Pulldown_pol_IO_lowcap_EN PAD_READ_PMOS ( .CIN(ReadPMOS), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(READ_PMOS_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_FREEZE_PMOS ( .CIN(FreezePMOS), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(FREEZE_PMOS_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_TOKEN_PMOS ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_PMOS_PAD), .SUB(PSUB), .DOUT(TokenPMOS), .OEN(conf.EN_OUT[1]) ); //TRANSMITTER (Default=enabled=0)
    Pulldown_pol_IO_lowcap_EN PAD_OUT_PMOS ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_PMOS_PAD), .SUB(PSUB), .DOUT(OutPMOS), .OEN(conf.EN_OUT[1]) ); //TRANSMITTER (Default=enabled=0)
//Diff PADS
    Pulldown_pol_IO_lowcap_EN PAD_nTOKEN_PMOS ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_PMOS_N_PAD), .SUB(PSUB), .DOUT(~TokenPMOS), .OEN(conf.nEN_OUT[1]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_nOUT_PMOS ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_PMOS_N_PAD), .SUB(PSUB), .DOUT(~OutPMOS), .OEN(conf.nEN_OUT[1]) ); //TRANSMITTER (Default=disabled=1)

// FLAVOR 3 (COMP) I/O       
    Pulldown_pol_IO_lowcap_EN PAD_READ_COMP ( .CIN(ReadCOMP), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(READ_COMP_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_FREEZE_COMP ( .CIN(FreezeCOMP), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(FREEZE_COMP_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_TOKEN_COMP ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_COMP_PAD), .SUB(PSUB), .DOUT(TokenCOMP), .OEN(conf.EN_OUT[2]) ); //TRANSMITTER (Default=enabled=0)
    Pulldown_pol_IO_lowcap_EN PAD_OUT_COMP ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_COMP_PAD), .SUB(PSUB), .DOUT(OutCOMP), .OEN(conf.EN_OUT[2]) ); //TRANSMITTER (Default=enabled=0)
//Diff PADS
    Pulldown_pol_IO_lowcap_EN PAD_nTOKEN_COMP ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_COMP_N_PAD), .SUB(PSUB), .DOUT(~TokenCOMP), .OEN(conf.nEN_OUT[2]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_nOUT_COMP ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_COMP_N_PAD), .SUB(PSUB), .DOUT(~OutCOMP), .OEN(conf.nEN_OUT[2]) ); //TRANSMITTER (Default=disabled=1)

// FLAVOR 4 (HV) I/O   
    Pulldown_pol_IO_lowcap_EN PAD_READ_HV ( .CIN(ReadHV), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(READ_HV_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_FREEZE_HV ( .CIN(FreezeHV), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(FREEZE_HV_PAD), .SUB(PSUB), .DOUT(), .OEN(1'b1) ); //RECEIVER (OEN=1 in the new PAD)
    Pulldown_pol_IO_lowcap_EN PAD_TOKEN_HV ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_HV_PAD), .SUB(PSUB), .DOUT(TokenHV), .OEN(conf.EN_OUT[3]) ); //TRANSMITTER (Default=enabled=0)
    Pulldown_pol_IO_lowcap_EN PAD_OUT_HV ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_HV_PAD), .SUB(PSUB), .DOUT(OutHV), .OEN(conf.EN_OUT[3]) ); //TRANSMITTER (Default=enabled=0)
//Diff PADS
    Pulldown_pol_IO_lowcap_EN PAD_nTOKEN_HV ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(TOKEN_HV_N_PAD), .SUB(PSUB), .DOUT(~TokenHV), .OEN(conf.nEN_OUT[3]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_nOUT_HV ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(OUT_HV_N_PAD), .SUB(PSUB), .DOUT(~OutHV), .OEN(conf.nEN_OUT[3]) ); //TRANSMITTER (Default=disabled=1)

// HITOR    
    Pulldown_pol_IO_lowcap_EN PAD_HIT_OR0 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_PAD[0]), .SUB(PSUB), .DOUT(HitOr[0]), .OEN(conf.EN_HITOR_OUT[0]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_HIT_OR1 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_PAD[1]), .SUB(PSUB), .DOUT(HitOr[1]), .OEN(conf.EN_HITOR_OUT[1]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_HIT_OR2 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_PAD[2]), .SUB(PSUB), .DOUT(HitOr[2]), .OEN(conf.EN_HITOR_OUT[2]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_HIT_OR3 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_PAD[3]), .SUB(PSUB), .DOUT(HitOr[3]), .OEN(conf.EN_HITOR_OUT[3]) ); //TRANSMITTER (Default=disabled=1)
//Diff PADS
    Pulldown_pol_IO_lowcap_EN PAD_nHIT_OR0 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_N_PAD[0]), .SUB(PSUB), .DOUT(~HitOr[0]), .OEN(conf.nEN_HITOR_OUT[0]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_nHIT_OR1 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_N_PAD[1]), .SUB(PSUB), .DOUT(~HitOr[1]), .OEN(conf.nEN_HITOR_OUT[1]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_nHIT_OR2 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_N_PAD[2]), .SUB(PSUB), .DOUT(~HitOr[2]), .OEN(conf.nEN_HITOR_OUT[2]) ); //TRANSMITTER (Default=disabled=1)
    Pulldown_pol_IO_lowcap_EN PAD_nHIT_OR3 ( .CIN(), .AVDD(VDDD), .AVSS(GNDD), .DVDD(VDDP), .DVSS(GNDP), .PAD(HIT_OR_N_PAD[3]), .SUB(PSUB), .DOUT(~HitOr[3]), .OEN(conf.nEN_HITOR_OUT[3]) ); //TRANSMITTER (Default=disabled=1)
        

    
// POWER PADS IN PERIPHERY GENERATED IN DIGITAL FLOW
    localparam DVDD_POWER_PADS = 55;
    localparam DVSS_POWER_PADS = 54;
    localparam DECOUPLING_CAP_FILLERS = 150;

    genvar i;
    generate 
        for (i=0;i<DVDD_POWER_PADS;i=i+1)
        begin : DIGITAL_P
           PAD_DVDD        INST_PAD_DVDD (.AVDD ( VDDD ), .AVSS ( GNDD ), .DVDD ( VDDP ), .DVSS ( GNDP ), .SUB ( PSUB ));
        end
   endgenerate

    genvar j;
    generate 
        for (j=0;j<DVSS_POWER_PADS;j=j+1)
        begin : DIGITAL_G
           PAD_DVSS        INST_PAD_DVSS (.AVDD ( VDDD ), .AVSS ( GNDD ), .DVDD ( VDDP ), .DVSS ( GNDP ), .SUB ( PSUB ));
        end
   endgenerate


// DECOUPLING FILLERS IN PERIPHERY GENERATED IN DIGITAL FLOW
    genvar k;
    generate 
        for (k=0;k<DECOUPLING_CAP_FILLERS;k=k+1)
        begin : FILLER
           decoupling_cap_filler  INST_decoupling_cap_filler (.AVDD ( VDDD ), .AVSS ( GNDD ), .DVDD ( VDDP ), .DVSS ( GNDP ), .SUB ( PSUB ));
        end
   endgenerate

    
    //
    //   CONFIGURATION
    //
    
    t_conf default_conf;
    always_comb begin

        //****DEFAULT CONFIGURATION****//
        //----------TEST PATTERN-------//
        default_conf.EN_TEST_PATTERN = '0;
        //----------READOUT ENABLE-----//
        default_conf.EN_PMOS_NOSF = '1;
        default_conf.EN_PMOS = '1;
        default_conf.EN_COMP = '1;
        default_conf.EN_HV = '1;
        default_conf.EN_OUT = '0;
        default_conf.nEN_OUT = '1;
        //--------HITOR OUT ENABLE-----//
        default_conf.EN_HITOR_OUT = '1;
        default_conf.nEN_HITOR_OUT = '1;
        //----------PULSING------------//
        default_conf.COL_PULSE_SEL = '0;
        default_conf.INJ_IN_MON_L = 0;
        default_conf.INJ_IN_MON_R = 0;
        default_conf.INJ_ROW = '0;
        //----------MASKING------------//
        default_conf.MASKV = '1;
        default_conf.MASKH = '1;  //(nMASKH=HITOR_SEL_ROW)
        default_conf.MASKD = '1;
        //------HIT_OR_COLUMN_ENABLE---//
        default_conf.DIG_MON_SEL = '0;
        //---------4-bit DAC-----------//
        //Value=16/(binary_to_decimal)*max current
        //1st stage
        default_conf.SET_IBUFP_L = 4'h5; // (30uA max, 2uA LSB, default=10uA)
        default_conf.SET_IBUFP_R = 4'h5; // (30uA max, 2uA LSB, default=10uA)
        //2nd stage - Driver
        default_conf.SET_IBUFN_L = 4'h9; // (300uA max, 20uA LSB, default=180uA)
        default_conf.SET_IBUFN_R = 4'h9; // (300uA max, 20uA LSB, default=180uA)

        //------------DAC-------------//
        //SET VOLTAGE DAC - ONE HOT ENCODING
        //VCASN, VCLIP no buffer
        //Source follower buffer for VRESETx, VH,VL. VRESET level shift=555mV, VL,VH level shift=385mV
        //VRESETxx max = #88 (1.25V + 0.55V), VH,VL max = #100 (1.415V+0.385V), VH,VL min = #36 (0.515V + 0.385V), VH>VL
        //Value = 1.8/127 * (#SET LINE (0 to 127) + S.F level shift), MAX=1.8V, LSB=14.17mV, MIN=S.F level shift
        default_conf.SET_VRESET_P = 128'h00000000000000000000000000010000; //(LINE #16 default=780mV (225mV+555mV))
        default_conf.SET_VH = 128'h00000000000080000000000000000000; //(LINE #79 default=1.5V (1.1V+385mV)
        default_conf.SET_VL = 128'h00000000000000000000100000000000; //(LINE #44 default=1V (620mV+385mV))
        default_conf.SET_VCASN = 128'h00000000000000000000010000000000; //(LINE #40 default=570mV)
        //NOT USED IN MONOPIX
        default_conf.SET_VRESET_D = 128'h00000000000000000000200000000000; //(LINE #45 default=1.19V (645mV+555mV))
        default_conf.SET_VCLIP = 128'h00000000000000000000000000000000; //(LINE #0 default=0V)

        //SET CURRENT DAC - THERMOMETER ENCODING, START FROM THE MIDDLE
        //Value = (#lines active)*max current/128
        default_conf.SET_IBIAS = {{41{1'b0}},{46{1'b1}},{41{1'b0}}}; // (1.4uA max, 10.9nA LSB, default = 500nA)
        default_conf.SET_IDB = {{49{1'b0}},{29{1'b1}},{50{1'b0}}}; // (2.24uA max, 17.5nA LSB, default = 500nA)
        default_conf.SET_ITHR = {{60{1'b0}},{8{1'b1}},{60{1'b0}}}; // (17.5nA max, 137pA LSB, default = 1.1nA)
        default_conf.SET_IRESET = {{56{1'b0}},{15{1'b1}},{57{1'b0}}}; //4.7// (4.375nA max, 34.2pA LSB, default = 512pA)
        default_conf.SET_ICASN = {{45{1'b0}},{38{1'b1}},{45{1'b0}}}; // (560nA max, 4.375nA LSB, default = 166nA) VCASN = 572mV
        //SET IRESET BIT (1= HIGH LEAKAGE MODE, 0=LOW LEAKAGE MODE)
        //LOW LEAKAGE -> 43.75pA max, 342fA LSB  HIGH LEAKAGE -> 4.375nA max, 34.2pA LSB
        default_conf.SET_IRESET_BIT = 1;

        //SET SWCNTL - MONITOR/OVERRIDE
        //SWCNTLxx    MONITOR SWCNTL    OPERATION
        //   0                0           NORMAL
        //   0                1           MONITOR
        //   1                0           OVERRIDE/NORMAL OTHERS
        //   1                1           OVERRIDE/MONITOR OTHERS
        //MONITOR SWCNTL
        default_conf.SWCNTL_DACMONI = 0;
        default_conf.SWCNTL_DACMONV = 0;
        //SWCNTLxx
        default_conf.SWCNTL_VRESET_P = 0;
        default_conf.SWCNTL_VH = 0;
        default_conf.SWCNTL_VL = 0;
        default_conf.SWCNTL_VCASN = 0;

        default_conf.SWCNTL_IREF = 0;
        default_conf.SWCNTL_IBIAS = 0;
        default_conf.SWCNTL_IDB = 0;
        default_conf.SWCNTL_ITHR = 0;
        default_conf.SWCNTL_IRESET = 0;
        default_conf.SWCNTL_ICASN = 0;
        //NOT USED IN MONOPIX
        default_conf.SWCNTL_VRESET_D = 0;
        default_conf.SWCNTL_VCLIP = 0;

    end 

    localparam CONF_SIZE = $bits(t_conf);
    cnfg_reg #(.SIZE(CONF_SIZE)) global_cnfg  (
            .DefConf(DefConf), 
            .clk(ClkConf), 
            .ld(LdConf), 
            .si(SiConf), 
            .so(SoConf),
            .DefVal(default_conf), 
            .Out(conf),
            .OutSr()
         );

    //
    //   MONOPIX_TOP
    //
    
    logic SET_IRESET_BIT;

    logic  SWCNTL_DACMONI; 
    logic  SWCNTL_DACMONV; 
    logic  SWCNTL_IBIAS; 
    logic  SWCNTL_ICASN;
    logic  SWCNTL_IDB; 
    logic  SWCNTL_IREF; 
    logic  SWCNTL_IRESET; 
    logic  SWCNTL_ITHR; 
    logic  SWCNTL_VCASN;
    logic  SWCNTL_VCLIP; 
    logic  SWCNTL_VH; 
    logic  SWCNTL_VL; 
    logic  SWCNTL_VRESET_D;
    logic  SWCNTL_VRESET_P;

    // HITOR monitoring
    logic [111:0]  DIG_MON_PMOS_NOSF;
    logic [111:0]  DIG_MON_PMOS;
    logic [111:0]  DIG_MON_COMP;
    logic [111:0]  DIG_MON_HV;
  
    //DAC
    logic [127:0]  SET_IBIAS;
    logic [127:0]  SET_IDB;
    logic [127:0]  SET_ITHR;
    logic [127:0]  SET_IRESET;
    logic [127:0]  SET_ICASN;

    logic [127:0]  SET_VRESET_P;
    logic [127:0]  SET_VH;
    logic [127:0]  SET_VL;
    logic [127:0]  SET_VCASN;
    logic [127:0]  SET_VRESET_D;
    logic [127:0]  SET_VCLIP;

    logic [3:0]  SET_IBUFP_L;
    logic [3:0]  SET_IBUFP_R;
    logic [3:0]  SET_IBUFN_L;
    logic [3:0]  SET_IBUFN_R;

    logic [447:0]  DIG_MON_SEL;
    logic [223:0]  INJ_ROW;

    //Matrix
    logic [447:0]  MASKV;
    logic [223:0]  MASKH;
    logic [447:0]  MASKD;

    //Pulsing
    logic [447:0]  INJ_IN;//PULSING DIGITAL 
    logic INJ_IN_MON_L; //PULSING extra
    logic INJ_IN_MON_R; //PULSING extra
    
   
    //Readout    
    logic [1343:0]  BcidMtx;
    
    logic [55:0]  nTOK_PMOS_NOSF;
    logic [55:0]  Read_PMOS_NOSF;
    logic [55:0]  FREEZE_PMOS_NOSF;
    logic [1175:0]  Data_PMOS_NOSF;

    logic [55:0]  nTOK_PMOS;
    logic [55:0]  FREEZE_PMOS;
    logic [55:0]  Read_PMOS;
    logic [1175:0]  Data_PMOS;

    logic [55:0]  nTOK_COMP;
    logic [55:0]  FREEZE_COMP;
    logic [55:0]  Read_COMP;
    logic [1175:0]  Data_COMP;
    
    logic [55:0]  nTOK_HV;
    logic [55:0]  FREEZE_HV;
    logic [55:0]  Read_HV;
    logic [1175:0]  Data_HV;
    

    MONOPIX_TOP MONOPIX_TOP ( 
	.DIG_MON_COMP ( DIG_MON_COMP ),
	.DIG_MON_HV ( DIG_MON_HV ),
	.DIG_MON_PMOS ( DIG_MON_PMOS ),
	.DIG_MON_PMOS_NOSF ( DIG_MON_PMOS_NOSF ),
	.Data_COMP ( Data_COMP ),
	.Data_HV ( Data_HV ),
	.Data_PMOS ( Data_PMOS ),
	.Data_PMOS_NOSF ( Data_PMOS_NOSF ),
	.nTOK_COMP ( nTOK_COMP ),
	.nTOK_HV ( nTOK_HV ),
	.nTOK_PMOS ( nTOK_PMOS ),
	.nTOK_PMOS_NOSF ( nTOK_PMOS_NOSF ),
	.BiasSF_PAD ( BiasSF_PAD ),
	.DACMON_IBIAS_PAD ( DACMON_IBIAS_PAD ),
	.DACMON_ICASN_PAD ( DACMON_ICASN_PAD ),
	.DACMON_IDB_PAD ( DACMON_IDB_PAD ),
	.DACMON_IRESET_PAD ( DACMON_IRESET_PAD ),
	.DACMON_ITHR_PAD ( DACMON_ITHR_PAD ),
	.DACMON_VCASN_DAC_PAD ( DACMON_VCASN_DAC_PAD ),
	.DACMON_VH_PAD ( DACMON_VH_PAD ),
	.DACMON_VL_PAD ( DACMON_VL_PAD ),
	.DACMON_VRESET_P_PAD ( DACMON_VRESET_P_PAD ),
	.GNDA ( GNDA ),
	.GNDA_DAC ( GNDA_DAC ),
	.GNDD ( GNDD ),
	//.GNDP ( GNDP ),
	.HV_DIODE ( HV_DIODE ),
	.OUTA_MON_L_PAD ( OUTA_MON_L_PAD ),
	.OUTA_MON_R_PAD ( OUTA_MON_R_PAD ),
	.PSUB ( PSUB ),
	.PWELL ( PWELL ),
	.VCASN_DAC_MON_L_PAD ( VCASN_DAC_MON_L_PAD ),
	.VCASN_DAC_MON_R_PAD ( VCASN_DAC_MON_R_PAD ),
	.VCASN_MON_L_PAD ( VCASN_MON_L_PAD ),
	.VCASN_MON_R_PAD ( VCASN_MON_R_PAD ),
	.VDDA ( VDDA ),
	.VDDA_DAC ( VDDA_DAC ),
	.VDDD ( VDDD ),
	//.VDDP ( VDDP ),
	.VPC_PAD ( VPC_PAD ),
	.VPCNOSF ( VPCNOSF ),
	.BcidMtx ( BcidMtx ),
	.DIG_MON_SEL ( DIG_MON_SEL ),
	.FREEZE_COMP ( FREEZE_COMP ),
	.FREEZE_HV ( FREEZE_HV ),
	.FREEZE_PMOS ( FREEZE_PMOS ),
	.FREEZE_PMOS_NOSF ( FREEZE_PMOS_NOSF ),
	.INJ_IN ( INJ_IN ),
	.INJ_IN_MON_L ( INJ_IN_MON_L ),
	.INJ_IN_MON_R ( INJ_IN_MON_R ),
	.INJ_ROW ( INJ_ROW ),
	.MASKD ( MASKD ),
	.MASKH ( MASKH ),
	.MASKV ( MASKV ),
	.Read_COMP ( Read_COMP ),
	.Read_HV ( Read_HV ),
	.Read_PMOS ( Read_PMOS ),
	.Read_PMOS_NOSF ( Read_PMOS_NOSF ),
	.SET_IBIAS ( SET_IBIAS ),
	.SET_IBUFN_L ( SET_IBUFN_L ),
	.SET_IBUFN_R ( SET_IBUFN_R ),
	.SET_IBUFP_L ( SET_IBUFP_L ),
	.SET_IBUFP_R ( SET_IBUFP_R ),
	.SET_ICASN ( SET_ICASN ),
	.SET_IDB ( SET_IDB ),
	.SET_IRESET ( SET_IRESET ),
	.SET_IRESET_BIT ( SET_IRESET_BIT ),
	.SET_ITHR ( SET_ITHR ),
	.SET_VCASN ( SET_VCASN ),
	.SET_VCLIP ( SET_VCLIP ),
	.SET_VH ( SET_VH ),
	.SET_VL ( SET_VL ),
	.SET_VRESET_D ( SET_VRESET_D ),
	.SET_VRESET_P ( SET_VRESET_P ),
	.SWCNTL_DACMONI ( SWCNTL_DACMONI ),
	.SWCNTL_DACMONV ( SWCNTL_DACMONV ),
	.SWCNTL_IBIAS ( SWCNTL_IBIAS ),
	.SWCNTL_ICASN ( SWCNTL_ICASN ),
	.SWCNTL_IDB ( SWCNTL_IDB ),
	.SWCNTL_IREF ( SWCNTL_IREF ),
	.SWCNTL_IRESET ( SWCNTL_IRESET ),
	.SWCNTL_ITHR ( SWCNTL_ITHR ),
	.SWCNTL_VCASN ( SWCNTL_VCASN ),
	.SWCNTL_VCLIP ( SWCNTL_VCLIP ),
	.SWCNTL_VH ( SWCNTL_VH ),
	.SWCNTL_VL ( SWCNTL_VL ),
	.SWCNTL_VRESET_D ( SWCNTL_VRESET_D ),
	.SWCNTL_VRESET_P ( SWCNTL_VRESET_P ),
	.nRST ( nRST ));


    always_comb begin
        //DAC
        SET_VRESET_P = conf.SET_VRESET_P;
        SET_VH  = conf.SET_VH;
        SET_VL = conf.SET_VL;
        SET_VCASN = conf.SET_VCASN;
        SET_VRESET_D = conf.SET_VRESET_D;
        SET_VCLIP = conf.SET_VCLIP;

        SET_IBIAS = conf.SET_IBIAS;
        SET_IDB = conf.SET_IDB;
        SET_ITHR = conf.SET_ITHR;
        SET_IRESET = conf.SET_IRESET;
        SET_ICASN = conf.SET_ICASN;

        SET_IRESET_BIT = conf.SET_IRESET_BIT;

        SET_IBUFN_L  = conf.SET_IBUFN_L;
        SET_IBUFN_R = conf.SET_IBUFN_R;
        SET_IBUFP_L  = conf.SET_IBUFP_L;
        SET_IBUFP_R  = conf.SET_IBUFP_R;
        
        SWCNTL_DACMONI  = conf.SWCNTL_DACMONI; 
        SWCNTL_DACMONV  = conf.SWCNTL_DACMONV; 
        SWCNTL_IBIAS  = conf.SWCNTL_IBIAS; 
        SWCNTL_ICASN  = conf.SWCNTL_ICASN;
        SWCNTL_IDB  = conf.SWCNTL_IDB; 
        SWCNTL_IREF  = conf.SWCNTL_IREF; 
        SWCNTL_IRESET  = conf.SWCNTL_IRESET; 
        SWCNTL_ITHR  = conf.SWCNTL_ITHR; 
        SWCNTL_VCASN  = conf.SWCNTL_VCASN;
        SWCNTL_VCLIP  = conf.SWCNTL_VCLIP; 
        SWCNTL_VH  = conf.SWCNTL_VH; 
        SWCNTL_VL  = conf.SWCNTL_VL; 
        SWCNTL_VRESET_D  = conf.SWCNTL_VRESET_D;
        SWCNTL_VRESET_P  = conf.SWCNTL_VRESET_P;
       
        //Matrix
        MASKV = conf.MASKV;
        MASKH = conf.MASKH;
        MASKD  = conf.MASKD;
        INJ_ROW = conf.INJ_ROW;
        DIG_MON_SEL = conf.DIG_MON_SEL;

        //Pulsing
        INJ_IN = {448{Pulse}} & (conf.COL_PULSE_SEL);
        INJ_IN_MON_L = Pulse & (conf.INJ_IN_MON_L);
        INJ_IN_MON_R = Pulse & (conf.INJ_IN_MON_R);
    end
    

    //
    //   READOUT
    //    
    logic reset_ff;
    always_ff@(posedge ClkBx)
        reset_ff <= ResetBcid;
    
    
    logic [5:0] bcid_bin;
    logic [5:0] bcid_gray;
    always_ff@(posedge ClkBx)
        if(reset_ff)
            bcid_bin <= 0;
        else
            bcid_bin <= bcid_bin +1;
    assign bcid_gray = (bcid_bin >> 1) ^ bcid_bin;

    wire [3:0][335:0] bcid_matrix_type;
    
    always_ff@(posedge ClkBx)
        BcidMtx <= bcid_matrix_type;
        
    readout readout_PMOS_NOSF
    (
        .ClkBx(ClkBx), 
        .ClkOut(ClkOut), 
        .Read(ReadPMOS_NOSF),
        .Freeze(FreezePMOS_NOSF), 
        .Bcid(bcid_gray),
        .EnTestPattern(conf.EN_TEST_PATTERN[0]),
        .Enable(conf.EN_PMOS_NOSF),
        .DataOut(OutPMOS_NOSF),
        .TokenOut(TokenPMOS_NOSF),
        .TokColB(nTOK_PMOS_NOSF),
        .DataCol(Data_PMOS_NOSF),
        .ReadCol(Read_PMOS_NOSF),
        .FreezeCol(FREEZE_PMOS_NOSF),
        .BcidCol(bcid_matrix_type[0])
    );
    
    readout readout_PMOS
    (
        .ClkBx(ClkBx), 
        .ClkOut(ClkOut), 
        .Read(ReadPMOS),
        .Freeze(FreezePMOS), 
        .Bcid(bcid_gray),
        .EnTestPattern(conf.EN_TEST_PATTERN[1]),
        .Enable(conf.EN_PMOS),
        .DataOut(OutPMOS),
        .TokenOut(TokenPMOS),
        .TokColB(nTOK_PMOS),
        .DataCol(Data_PMOS),
        .ReadCol(Read_PMOS),
        .FreezeCol(FREEZE_PMOS),
        .BcidCol(bcid_matrix_type[1])
    );
    
    readout readout_COMP
    (
        .ClkBx(ClkBx), 
        .ClkOut(ClkOut), 
        .Read(ReadCOMP),
        .Freeze(FreezeCOMP), 
        .Bcid(bcid_gray),
        .EnTestPattern(conf.EN_TEST_PATTERN[2]),
        .Enable(conf.EN_COMP),
        .DataOut(OutCOMP),
        .TokenOut(TokenCOMP),
        .TokColB(nTOK_COMP),
        .DataCol(Data_COMP),
        .ReadCol(Read_COMP),
        .FreezeCol(FREEZE_COMP),
        .BcidCol(bcid_matrix_type[2])
    );
    
    readout readout_HV
    (
        .ClkBx(ClkBx), 
        .ClkOut(ClkOut), 
        .Read(ReadHV),
        .Freeze(FreezeHV), 
        .Bcid(bcid_gray),
        .EnTestPattern(conf.EN_TEST_PATTERN[3]),
        .Enable(conf.EN_HV),
        .DataOut(OutHV),
        .TokenOut(TokenHV),
        .TokColB(nTOK_HV),
        .DataCol(Data_HV),
        .ReadCol(Read_HV),
        .FreezeCol(FREEZE_HV),
        .BcidCol(bcid_matrix_type[3])
    );
    
    
    
    always_comb begin
        HitOr[0] = |DIG_MON_PMOS_NOSF;
        HitOr[1] = |DIG_MON_PMOS;
        HitOr[2] = |DIG_MON_COMP;
        HitOr[3] = |DIG_MON_HV;
    end

endmodule
