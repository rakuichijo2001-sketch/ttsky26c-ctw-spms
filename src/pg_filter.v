/*
 * CTW-SPMS symmetric Power-Good (PG) stability filter.
 * PG_GOOD changes only after the synchronized input has held the opposite
 * value for the configured number of shared 100 us timer samples. A setting
 * of zero qualifies after one sampled timer tick.
 */

`default_nettype none

module pg_filter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       timer_tick_ce,
    input  wire       pg_sync,
    input  wire [7:0] stable_count_cfg,
    output reg        pg_good
);

    reg       candidate_value;
    reg [7:0] stable_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            candidate_value <= 1'b0;
            stable_count    <= 8'h00;
            pg_good         <= 1'b0;
        end else if (timer_tick_ce) begin
            if (pg_sync == pg_good) begin
                candidate_value <= pg_sync;
                stable_count    <= 8'h00;
            end else if (pg_sync != candidate_value) begin
                candidate_value <= pg_sync;
                if (stable_count_cfg <= 8'd1) begin
                    pg_good      <= pg_sync;
                    stable_count <= 8'h00;
                end else begin
                    stable_count <= 8'd1;
                end
            end else if ((stable_count_cfg <= 8'd1) ||
                         (stable_count >= (stable_count_cfg - 8'd1))) begin
                pg_good      <= candidate_value;
                stable_count <= 8'h00;
            end else if (stable_count != 8'hff) begin
                stable_count <= stable_count + 8'd1;
            end
        end
    end

endmodule

`default_nettype wire
