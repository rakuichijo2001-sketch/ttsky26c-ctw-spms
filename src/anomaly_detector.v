/* CTW-SPMS persistent warning and severe-anomaly qualification. */

`default_nettype none

module anomaly_detector (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       sample_strobe,
    input  wire [7:0] deviation,
    input  wire [7:0] warn_threshold,
    input  wire [7:0] fault_threshold,
    input  wire [7:0] warn_persist_count,
    input  wire [7:0] fault_persist_count,
    output reg        warning_active,
    output reg        fault_active
);

    reg [7:0] warn_count;
    reg [7:0] fault_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            warn_count     <= 8'h00;
            fault_count    <= 8'h00;
            warning_active <= 1'b0;
            fault_active   <= 1'b0;
        end else if (sample_strobe) begin
            if (deviation >= warn_threshold) begin
                if (warn_count != 8'hff) begin
                    warn_count <= warn_count + 8'd1;
                end
                if ((warn_persist_count <= 8'd1) ||
                    (warn_count >= (warn_persist_count - 8'd1))) begin
                    warning_active <= 1'b1;
                end
            end else begin
                warn_count     <= 8'h00;
                warning_active <= 1'b0;
            end

            if (deviation >= fault_threshold) begin
                if (fault_count != 8'hff) begin
                    fault_count <= fault_count + 8'd1;
                end
                if ((fault_persist_count <= 8'd1) ||
                    (fault_count >= (fault_persist_count - 8'd1))) begin
                    fault_active <= 1'b1;
                end
            end else begin
                fault_count  <= 8'h00;
                fault_active <= 1'b0;
            end
        end
    end

endmodule

`default_nettype wire
