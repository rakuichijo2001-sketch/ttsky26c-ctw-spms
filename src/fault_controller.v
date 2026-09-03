/*
 * CTW-SPMS fault latch, diagnostics, automatic retry and fault lock.
 * RETRY_DELAY is expressed in shared 100 us timer ticks.
 */

`default_nettype none

module fault_controller (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       timer_tick_ce,
    input  wire       system_request,
    input  wire       sequencer_run,
    input  wire       clear_fault,
    input  wire       fault_valid,
    input  wire [3:0] fault_code,
    input  wire [2:0] fault_detail,
    input  wire [7:0] retry_delay,
    input  wire [7:0] max_retry,
    output reg        fault_latched,
    output reg        fault_lock,
    output reg        retry_pulse,
    output reg  [3:0] last_fault,
    output reg  [7:0] fault_count,
    output reg  [7:0] retry_count,
    output reg  [2:0] last_fault_detail
);

    localparam [1:0] FC_NORMAL = 2'd0;
    localparam [1:0] FC_WAIT   = 2'd1;
    localparam [1:0] FC_HOLD   = 2'd2;
    localparam [1:0] FC_LOCK   = 2'd3;

    reg [1:0] controller_state;
    reg [7:0] retry_timer;
    reg       retry_episode_active;
    reg       retry_delay_done;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            controller_state    <= FC_NORMAL;
            retry_timer         <= 8'h00;
            retry_episode_active <= 1'b0;
            retry_delay_done    <= 1'b0;
            fault_latched       <= 1'b0;
            fault_lock          <= 1'b0;
            retry_pulse         <= 1'b0;
            last_fault          <= 4'h0;
            fault_count         <= 8'h00;
            retry_count         <= 8'h00;
            last_fault_detail   <= 3'd0;
        end else begin
            retry_pulse <= 1'b0;

            case (controller_state)
                FC_NORMAL: begin
                    fault_latched <= 1'b0;
                    fault_lock    <= 1'b0;
                    retry_timer   <= 8'h00;
                    retry_delay_done <= 1'b0;

                    if (fault_valid) begin
                        fault_latched <= 1'b1;
                        last_fault    <= fault_code;
                        last_fault_detail <= fault_detail;
                        if (fault_count != 8'hff) begin
                            fault_count <= fault_count + 8'd1;
                        end
                        if (!retry_episode_active) begin
                            retry_count <= 8'h00;
                        end
                        retry_episode_active <= 1'b1;

                        if (max_retry == 8'd0) begin
                            controller_state <= FC_HOLD;
                        end else begin
                            controller_state <= FC_WAIT;
                        end
                    end else if (sequencer_run) begin
                        retry_episode_active <= 1'b0;
                    end else if (clear_fault) begin
                        retry_episode_active <= 1'b0;
                        retry_count          <= 8'h00;
                    end
                end

                FC_WAIT: begin
                    fault_latched <= 1'b1;
                    fault_lock    <= 1'b0;

                    if (clear_fault && !fault_valid) begin
                        fault_latched        <= 1'b0;
                        retry_timer          <= 8'h00;
                        retry_count          <= 8'h00;
                        retry_episode_active <= 1'b0;
                        retry_delay_done     <= 1'b0;
                        controller_state     <= FC_NORMAL;
                        retry_pulse          <= system_request;
                    end else if (max_retry == 8'd0) begin
                        retry_timer       <= 8'h00;
                        retry_delay_done  <= 1'b0;
                        controller_state  <= FC_HOLD;
                    end else if (!system_request) begin
                        retry_timer      <= 8'h00;
                        retry_delay_done <= 1'b0;
                    end else if (!retry_delay_done) begin
                        if (retry_delay == 8'd0) begin
                            retry_delay_done <= 1'b1;
                        end else if (timer_tick_ce &&
                                     (retry_timer >= (retry_delay - 8'd1))) begin
                            retry_timer      <= 8'h00;
                            retry_delay_done <= 1'b1;
                        end else if (timer_tick_ce &&
                                     (retry_timer != 8'hff)) begin
                            retry_timer <= retry_timer + 8'd1;
                        end
                    end else if (!fault_valid) begin
                        retry_timer      <= 8'h00;
                        retry_delay_done <= 1'b0;
                        if (retry_count < max_retry) begin
                            if (retry_count != 8'hff) begin
                                retry_count <= retry_count + 8'd1;
                            end
                            fault_latched    <= 1'b0;
                            controller_state <= FC_NORMAL;
                            retry_pulse      <= 1'b1;
                        end else begin
                            fault_lock       <= 1'b1;
                            fault_latched    <= 1'b1;
                            controller_state <= FC_LOCK;
                        end
                    end
                end

                FC_HOLD: begin
                    fault_latched   <= 1'b1;
                    fault_lock      <= 1'b0;
                    retry_timer     <= 8'h00;
                    retry_delay_done <= 1'b0;
                    if (clear_fault && !fault_valid) begin
                        fault_latched        <= 1'b0;
                        retry_count          <= 8'h00;
                        retry_episode_active <= 1'b0;
                        controller_state     <= FC_NORMAL;
                        retry_pulse          <= system_request;
                    end else if (max_retry != 8'd0) begin
                        controller_state <= FC_WAIT;
                    end
                end

                FC_LOCK: begin
                    fault_latched <= 1'b1;
                    fault_lock    <= 1'b1;
                    retry_timer   <= 8'h00;
                    retry_delay_done <= 1'b0;
                    if (clear_fault && !fault_valid) begin
                        fault_latched        <= 1'b0;
                        fault_lock           <= 1'b0;
                        retry_count          <= 8'h00;
                        retry_episode_active <= 1'b0;
                        controller_state     <= FC_NORMAL;
                        retry_pulse          <= system_request;
                    end
                end

                default: begin
                    controller_state <= FC_LOCK;
                    fault_latched    <= 1'b1;
                    fault_lock       <= 1'b1;
                    retry_timer      <= 8'h00;
                    retry_delay_done <= 1'b0;
                end
            endcase
        end
    end

endmodule

`default_nettype wire
