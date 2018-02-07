
`ifndef DEFINES_SV
`define DEFINES_SV

typedef struct packed {
    
    logic [447:0]   COL_PULSE_SEL;
    logic [0:0]     INJ_IN_MON_L;
    logic [0:0]     INJ_IN_MON_R;
        
    logic [223:0]    INJ_ROW;
    logic [447:0]    MASKV;
    logic [223:0]    MASKH;
    logic [447:0]    MASKD;
    logic [447:0]    DIG_MON_SEL;
    
    logic [127:0]    SET_IBIAS;
    logic [127:0]    SET_IDB;
    logic [127:0]    SET_ITHR;
    logic [127:0]    SET_IRESET;
    logic [127:0]    SET_ICASN;
    
    logic [127:0]    SET_VRESET_P;
    logic [127:0]    SET_VH;
    logic [127:0]    SET_VL;
    logic [127:0]    SET_VCASN;
    logic [127:0]    SET_VRESET_D;
    logic [127:0]    SET_VCLIP;

    logic [0:0]      SET_IRESET_BIT;
    
    logic [3:0]  SET_IBUFN_R;
    logic [3:0]  SET_IBUFP_R;
    logic [3:0]  SET_IBUFP_L;
    logic [3:0]  SET_IBUFN_L;
    
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
    
    logic [3:0] EN_TEST_PATTERN;
    
    logic [55:0] EN_PMOS_NOSF;
    logic [55:0] EN_PMOS;
    logic [55:0] EN_COMP;
    logic [55:0] EN_HV;
    
    logic [3:0] EN_OUT;
    logic [3:0] nEN_OUT;
    logic [3:0] EN_HITOR_OUT;
    logic [3:0] nEN_HITOR_OUT;
} t_conf;

`endif // DEFINES_SV
