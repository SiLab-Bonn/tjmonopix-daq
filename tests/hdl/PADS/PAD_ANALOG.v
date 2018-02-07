//Verilog HDL for "pALPIDEfs_V2_BLOCKS_CAM", "PAD_ANALOG" "functional"
`timescale 1ns / 1ps

module PAD_ANALOG ( AVDD, AVSS, CIN, DVDD, DVSS, PAD, SUB );

  inout PAD;
  inout DVDD;
  inout CIN;
  inout AVSS;
  inout SUB;
  inout DVSS;
  inout AVDD;
endmodule
