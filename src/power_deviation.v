/* CTW-SPMS unsigned absolute power deviation. */

`default_nettype none

module power_deviation (
    input  wire [7:0] filtered_sample,
    input  wire [7:0] power_nominal,
    output wire [7:0] deviation
);

    assign deviation = (filtered_sample >= power_nominal) ?
                       (filtered_sample - power_nominal) :
                       (power_nominal - filtered_sample);

endmodule

`default_nettype wire
