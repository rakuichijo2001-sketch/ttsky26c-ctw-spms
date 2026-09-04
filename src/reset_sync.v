/*
 * CTW-SPMS reset synchronizer.
 *
 * The external active-low reset asserts the internal reset asynchronously.
 * Release is delayed through two flip-flops and therefore occurs only after
 * a core-clock edge.  This prevents recovery/removal ambiguity when rst_n is
 * released without a defined phase relationship to clk.
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module reset_sync (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);

    reg release_ff1;
    reg release_ff2;

    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n) begin
            release_ff1 <= 1'b0;
            release_ff2 <= 1'b0;
        end else begin
            release_ff1 <= 1'b1;
            release_ff2 <= release_ff1;
        end
    end

    assign sync_rst_n = release_ff2;

endmodule

`default_nettype wire
