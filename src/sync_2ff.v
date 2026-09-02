/*
 * CTW-SPMS reusable two-flip-flop synchronizer.
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module sync_2ff #(
    parameter RESET_VALUE = 1'b0
) (
    input  wire clk,
    input  wire rst_n,
    input  wire async_in,
    output wire sync_out
);

    reg sync_ff1;
    reg sync_ff2;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync_ff1 <= RESET_VALUE;
            sync_ff2 <= RESET_VALUE;
        end else begin
            sync_ff1 <= async_in;
            sync_ff2 <= sync_ff1;
        end
    end

    assign sync_out = sync_ff2;

endmodule

`default_nettype wire
