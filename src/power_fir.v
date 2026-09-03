/*
 * CTW-SPMS multiplier-free four-tap unity-gain moving average.
 *
 * A completed write to POWER_SAMPLE advances the filter exactly once:
 *   y[n] = (x[n] + x[n-1] + x[n-2] + x[n-3]) >> 2
 *
 * The first accepted sample fills all four taps, avoiding a false startup
 * transient. FILTERED_VALID stays low until that first sample is accepted.
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module power_fir (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       sample_strobe,
    input  wire [7:0] sample_in,
    output reg  [7:0] filtered_sample,
    output reg        filtered_valid,
    output reg        filtered_strobe
);

    reg [7:0] sample_d1;
    reg [7:0] sample_d2;
    reg [7:0] sample_d3;

    wire [9:0] moving_sum;

    assign moving_sum = {2'b00, sample_in} +
                        {2'b00, sample_d1} +
                        {2'b00, sample_d2} +
                        {2'b00, sample_d3};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sample_d1 <= 8'h00;
            sample_d2 <= 8'h00;
            sample_d3 <= 8'h00;
            filtered_sample <= 8'h00;
            filtered_valid  <= 1'b0;
            filtered_strobe <= 1'b0;
        end else begin
            filtered_strobe <= 1'b0;
            if (sample_strobe) begin
                filtered_valid  <= 1'b1;
                filtered_strobe <= 1'b1;
                if (!filtered_valid) begin
                    sample_d1       <= sample_in;
                    sample_d2       <= sample_in;
                    sample_d3       <= sample_in;
                    filtered_sample <= sample_in;
                end else begin
                    sample_d1       <= sample_in;
                    sample_d2       <= sample_d1;
                    sample_d3       <= sample_d2;
                    filtered_sample <= moving_sum[9:2];
                end
            end
        end
    end

endmodule

`default_nettype wire
