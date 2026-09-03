/* CTW-SPMS toggle/edge watchdog using the shared 100 us timer tick. */

`default_nettype none

module watchdog (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       timer_tick_ce,
    input  wire       enable,
    input  wire       heartbeat,
    input  wire [7:0] timeout_cfg,
    output reg        timeout_fault
);

    reg       heartbeat_d;
    reg [7:0] timeout_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            heartbeat_d  <= 1'b0;
            timeout_count <= 8'h00;
            timeout_fault <= 1'b0;
        end else begin
            heartbeat_d <= heartbeat;
            if (!enable || (timeout_cfg == 8'd0)) begin
                timeout_count <= 8'h00;
                timeout_fault <= 1'b0;
            end else if (heartbeat != heartbeat_d) begin
                timeout_count <= 8'h00;
                timeout_fault <= 1'b0;
            end else if (timer_tick_ce) begin
                if (timeout_count >= (timeout_cfg - 8'd1)) begin
                    timeout_fault <= 1'b1;
                end else begin
                    timeout_count <= timeout_count + 8'd1;
                end
            end
        end
    end

endmodule

`default_nettype wire
