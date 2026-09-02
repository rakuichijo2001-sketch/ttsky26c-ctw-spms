/* CTW-SPMS programmable four-level power classifier. */

`default_nettype none

module power_level_classifier (
    input  wire [7:0] filtered_sample,
    input  wire [7:0] high_threshold,
    input  wire [7:0] med_threshold,
    input  wire [7:0] low_threshold,
    output reg  [1:0] power_level
);

    localparam [1:0] POWER_CRITICAL = 2'b00;
    localparam [1:0] POWER_LOW      = 2'b01;
    localparam [1:0] POWER_MEDIUM   = 2'b10;
    localparam [1:0] POWER_HIGH     = 2'b11;

    always @* begin
        if (filtered_sample >= high_threshold) begin
            power_level = POWER_HIGH;
        end else if (filtered_sample >= med_threshold) begin
            power_level = POWER_MEDIUM;
        end else if (filtered_sample >= low_threshold) begin
            power_level = POWER_LOW;
        end else begin
            power_level = POWER_CRITICAL;
        end
    end

endmodule

`default_nettype wire
