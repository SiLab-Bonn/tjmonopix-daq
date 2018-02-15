
module serializer (
            input wire ClkBx, ClkOut, Read, EnTestPattern,
            input wire [26:0] DataIn,
            output wire DataOut
          );

reg [1:0] Read_dly;
always@(posedge ClkBx)
    Read_dly[1:0] <= {Read_dly[0], Read};
    
reg [1:0] Read_Out_dly;
always@(posedge ClkOut)
    Read_Out_dly <= {Read_Out_dly[0], Read_dly[1]};
    
reg load;
always@(posedge ClkOut)
    load <= Read_Out_dly[0] & !Read_Out_dly[1];

reg [26:0] ser;
always@(posedge ClkOut)
    if(load)
        if(EnTestPattern)
            ser <= 27'b100_10101010_11001100_00001111;
        else
            ser <= DataIn;
    else
        ser <= {ser[25:0], 1'b0};
        
assign DataOut = ser[26];
          
endmodule
