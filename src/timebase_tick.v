/*
 * CTW-SPMS 10 kHz clock-enable timebase from the 10 MHz system clock.
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module timebase_tick (
    input  wire clk,
    input  wire rst_n,
    output reg  timer_tick_ce
);

    reg [9:0] divider_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            divider_count <= 10'd0;
            timer_tick_ce  <= 1'b0;
        end else if (divider_count == 10'd999) begin
            divider_count <= 10'd0;
            timer_tick_ce  <= 1'b1;
        end else begin
            divider_count <= divider_count + 10'd1;
            timer_tick_ce  <= 1'b0;
        end
    end

endmodule

`default_nettype wire
