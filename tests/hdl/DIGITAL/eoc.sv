
module eoc #(parameter ADDR=0)  (
            input wire TokInChip, TokInCol, Read,
            output wire  TokOutChip, ReadCol,

            output wire [5:0] ColAddrOut,
            input wire [5:0] ColAddrIn,

            output wire [20:0] ColDataOut,
            input wire [20:0] ColDataIn,
            input wire [20:0] ColData,

            input wire [5:0] Bcid,
            output wire [5:0] BcidCol,

            input wire Enable
          );


wire TokInColEn;
assign TokInColEn = TokInCol & Enable;

assign TokOutChip = TokInColEn | TokInChip;

reg beeze_prev_int;
always@(Read or TokInChip)
if(!Read)
   beeze_prev_int = TokInChip;
   
reg beeze_col_int;
always@(Read or TokInColEn)
if(!Read)
   beeze_col_int = TokInColEn;
   
wire this_col_read;
assign this_col_read = (beeze_prev_int==0 && beeze_col_int==1);

assign ReadCol = this_col_read & Read & Enable; 

reg this_token_save;
always@(posedge Read) 
    this_token_save <= TokInColEn & !TokInChip;

wire [5:0] addr_this;
assign addr_this = this_token_save ? ADDR[5:0] : 0;
assign ColAddrOut = addr_this | ColAddrIn;

wire [20:0] data_this;
assign data_this = this_token_save ? ColData : 0;
assign ColDataOut = data_this | ColDataIn;

assign BcidCol = Bcid & {6{Enable}};

endmodule 
