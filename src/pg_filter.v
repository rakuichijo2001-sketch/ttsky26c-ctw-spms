/*
 * CTW-SPMS Power-Good (PG) assertion filter.
 * A deassertion removes GOOD on the first synchronized low sample.
 * A configured count of zero or one accepts the first synchronized high.
 */

`default_nettype none

module pg_filter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       pg_sync,
    input  wire [7:0] stable_count_cfg,
    output reg        pg_good
);

    reg [7:0] high_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            high_count <= 8'h00;
            pg_good    <= 1'b0;
        end else if (!pg_sync) begin
            high_count <= 8'h00;
            pg_good    <= 1'b0;
        end else begin
            if (high_count != 8'hff) begin
                high_count <= high_count + 8'd1;
            end
            if ((stable_count_cfg <= 8'd1) ||
                (high_count >= (stable_count_cfg - 8'd1))) begin
                pg_good <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
