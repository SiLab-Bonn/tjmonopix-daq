
module  cnfg_reg #(parameter SIZE = 1) 
                    ( 
                       input DefConf, clk, ld, si,
                       output wire so,
                       input [SIZE-1:0] DefVal,
                       output reg [SIZE-1:0] Out, OutSr
                   );    

always@(posedge clk)
    OutSr <= {OutSr[SIZE-2:0], si};
    
assign so = OutSr[SIZE-1];

reg [SIZE-1:0] Latch;
always@(*)
    if(ld)
        Latch = OutSr; 

assign Out = DefConf ?  DefVal : Latch ; 


endmodule
