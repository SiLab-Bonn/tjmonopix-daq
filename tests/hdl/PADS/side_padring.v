module side_padring ( CMOS_IN_B, CMOS_IN_T, AVDD, AVSS, DAC_VDD, DAC_VSS, DVDD,
DVSS, PAD_CMOS_B, PAD_CMOS_T, PAD_FEMON, PWELL, SUB, CMOS_OEN_B, CMOS_OEN_T,
CMOS_OUT_B, CMOS_OUT_T, FEMON );

  inout  [3:0] PAD_FEMON;
  inout  [39:0] PAD_CMOS_B;
  inout DAC_VSS;
  output  [39:0] CMOS_IN_B;
  input  [39:0] CMOS_OUT_T;
  inout PWELL;
  inout DVDD;
  input  [3:0] FEMON;
  input  [39:0] CMOS_OUT_B;
  input CMOS_OEN_T;
  input CMOS_OEN_B;
  inout  [39:0] PAD_CMOS_T;
  inout DAC_VDD;
  inout AVSS;
  output  [39:0] CMOS_IN_T;
  inout SUB;
  inout DVSS;
  inout AVDD;
endmodule
