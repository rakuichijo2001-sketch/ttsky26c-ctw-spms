/*
 * CTW-SPMS multiplier-free four-tap power sample filter.
 * y[n] = (x[n] + 2*x[n-1] + 2*x[n-2] + x[n-3]) / 4
 *
 * The coefficient sum is six, so the scaled result can exceed eight bits.
 * The externally visible result is intentionally saturated at 8'hff.
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module power_fir (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] sample_in,
    output wire [7:0] filtered_sample
);

    reg [7:0] sample_d1;
    reg [7:0] sample_d2;
    reg [7:0] sample_d3;

    wire [10:0] tap0;
    wire [10:0] tap1;
    wire [10:0] tap2;
    wire [10:0] tap3;
    wire [10:0] accumulator;
    wire [8:0]  scaled_sample;
    wire [1:0]  _unused_fraction;

    assign tap0 = {3'b000, sample_in};
    assign tap1 = {2'b00, sample_d1, 1'b0};
    assign tap2 = {2'b00, sample_d2, 1'b0};
    assign tap3 = {3'b000, sample_d3};
    assign accumulator = tap0 + tap1 + tap2 + tap3;
    assign scaled_sample = accumulator[10:2];
    assign _unused_fraction = accumulator[1:0];
    assign filtered_sample = scaled_sample[8] ? 8'hff : scaled_sample[7:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sample_d1 <= 8'h00;
            sample_d2 <= 8'h00;
            sample_d3 <= 8'h00;
        end else begin
            sample_d1 <= sample_in;
            sample_d2 <= sample_d1;
            sample_d3 <= sample_d2;
        end
    end

endmodule

`default_nettype wire
