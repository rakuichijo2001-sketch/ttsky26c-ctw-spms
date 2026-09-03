/* CTW-SPMS four-rail startup and reverse-shutdown sequencer. */

`default_nettype none

module rail_sequencer (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       timer_tick_ce,
    input  wire       system_request,
    input  wire       fault_shutdown,
    input  wire [3:0] pg_good,
    input  wire [7:0] sequence_delay,
    input  wire [7:0] startup_timeout,
    output reg  [3:0] rail_en,
    output reg  [4:0] current_state,
    output reg        fault_strobe,
    output reg  [3:0] fault_code,
    output reg  [2:0] fault_detail
);

    localparam [4:0] ST_OFF         = 5'd0;
    localparam [4:0] ST_RAIL1_START = 5'd1;
    localparam [4:0] ST_WAIT_PG1    = 5'd2;
    localparam [4:0] ST_RAIL2_START = 5'd3;
    localparam [4:0] ST_WAIT_PG2    = 5'd4;
    localparam [4:0] ST_RAIL3_START = 5'd5;
    localparam [4:0] ST_WAIT_PG3    = 5'd6;
    localparam [4:0] ST_RAIL4_START = 5'd7;
    localparam [4:0] ST_WAIT_PG4    = 5'd8;
    localparam [4:0] ST_RUN         = 5'd9;
    localparam [4:0] ST_SHUTDOWN_R4 = 5'd10;
    localparam [4:0] ST_SHUTDOWN_R3 = 5'd11;
    localparam [4:0] ST_SHUTDOWN_R2 = 5'd12;
    localparam [4:0] ST_SHUTDOWN_R1 = 5'd13;
    localparam [4:0] ST_FAULT       = 5'd14;

    localparam [3:0] FAULT_PG1             = 4'h1;
    localparam [3:0] FAULT_PG2             = 4'h2;
    localparam [3:0] FAULT_PG3             = 4'h3;
    localparam [3:0] FAULT_PG4             = 4'h4;
    localparam [3:0] FAULT_STARTUP_TIMEOUT = 4'h5;

    reg [7:0] sequence_count;
    reg [7:0] timeout_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rail_en       <= 4'b0000;
            current_state <= ST_OFF;
            fault_strobe  <= 1'b0;
            fault_code    <= 4'h0;
            fault_detail  <= 3'd0;
            sequence_count <= 8'h00;
            timeout_count <= 8'h00;
        end else begin
            fault_strobe <= 1'b0;

            if (fault_shutdown) begin
                rail_en        <= 4'b0000;
                current_state  <= ST_FAULT;
                sequence_count <= 8'h00;
                timeout_count  <= 8'h00;
            end else begin
                case (current_state)
                    ST_OFF: begin
                        rail_en        <= 4'b0000;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        if (system_request) begin
                            current_state <= ST_RAIL1_START;
                        end
                    end

                    ST_RAIL1_START: begin
                        rail_en        <= 4'b0001;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        current_state  <= system_request ? ST_WAIT_PG1 : ST_SHUTDOWN_R1;
                    end

                    ST_WAIT_PG1: begin
                        rail_en <= 4'b0001;
                        if (!system_request) begin
                            sequence_count <= 8'h00;
                            timeout_count  <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R1;
                        end else if (pg_good[0]) begin
                            if (sequence_delay == 8'd0) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RAIL2_START;
                            end else if (timer_tick_ce &&
                                         (sequence_count >=
                                          (sequence_delay - 8'd1))) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RAIL2_START;
                            end else if (timer_tick_ce &&
                                         (sequence_count != 8'hff)) begin
                                sequence_count <= sequence_count + 8'd1;
                            end
                        end else begin
                            sequence_count <= 8'h00;
                            if ((startup_timeout != 8'd0) && timer_tick_ce) begin
                                if (timeout_count >=
                                    (startup_timeout - 8'd1)) begin
                                    fault_strobe  <= 1'b1;
                                    fault_code    <= FAULT_STARTUP_TIMEOUT;
                                    fault_detail  <= 3'd1;
                                    timeout_count <= 8'h00;
                                end else if (timeout_count != 8'hff) begin
                                    timeout_count <= timeout_count + 8'd1;
                                end
                            end
                        end
                    end

                    ST_RAIL2_START: begin
                        rail_en        <= 4'b0011;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        current_state  <= system_request ? ST_WAIT_PG2 : ST_SHUTDOWN_R2;
                    end

                    ST_WAIT_PG2: begin
                        rail_en <= 4'b0011;
                        if (!system_request) begin
                            sequence_count <= 8'h00;
                            timeout_count  <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R2;
                        end else if (pg_good[1]) begin
                            if (sequence_delay == 8'd0) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RAIL3_START;
                            end else if (timer_tick_ce &&
                                         (sequence_count >=
                                          (sequence_delay - 8'd1))) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RAIL3_START;
                            end else if (timer_tick_ce &&
                                         (sequence_count != 8'hff)) begin
                                sequence_count <= sequence_count + 8'd1;
                            end
                        end else begin
                            sequence_count <= 8'h00;
                            if ((startup_timeout != 8'd0) && timer_tick_ce) begin
                                if (timeout_count >=
                                    (startup_timeout - 8'd1)) begin
                                    fault_strobe  <= 1'b1;
                                    fault_code    <= FAULT_STARTUP_TIMEOUT;
                                    fault_detail  <= 3'd2;
                                    timeout_count <= 8'h00;
                                end else if (timeout_count != 8'hff) begin
                                    timeout_count <= timeout_count + 8'd1;
                                end
                            end
                        end
                    end

                    ST_RAIL3_START: begin
                        rail_en        <= 4'b0111;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        current_state  <= system_request ? ST_WAIT_PG3 : ST_SHUTDOWN_R3;
                    end

                    ST_WAIT_PG3: begin
                        rail_en <= 4'b0111;
                        if (!system_request) begin
                            sequence_count <= 8'h00;
                            timeout_count  <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R3;
                        end else if (pg_good[2]) begin
                            if (sequence_delay == 8'd0) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RAIL4_START;
                            end else if (timer_tick_ce &&
                                         (sequence_count >=
                                          (sequence_delay - 8'd1))) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RAIL4_START;
                            end else if (timer_tick_ce &&
                                         (sequence_count != 8'hff)) begin
                                sequence_count <= sequence_count + 8'd1;
                            end
                        end else begin
                            sequence_count <= 8'h00;
                            if ((startup_timeout != 8'd0) && timer_tick_ce) begin
                                if (timeout_count >=
                                    (startup_timeout - 8'd1)) begin
                                    fault_strobe  <= 1'b1;
                                    fault_code    <= FAULT_STARTUP_TIMEOUT;
                                    fault_detail  <= 3'd3;
                                    timeout_count <= 8'h00;
                                end else if (timeout_count != 8'hff) begin
                                    timeout_count <= timeout_count + 8'd1;
                                end
                            end
                        end
                    end

                    ST_RAIL4_START: begin
                        rail_en        <= 4'b1111;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        current_state  <= system_request ? ST_WAIT_PG4 : ST_SHUTDOWN_R4;
                    end

                    ST_WAIT_PG4: begin
                        rail_en <= 4'b1111;
                        if (!system_request) begin
                            sequence_count <= 8'h00;
                            timeout_count  <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R4;
                        end else if (pg_good[3]) begin
                            if (sequence_delay == 8'd0) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RUN;
                            end else if (timer_tick_ce &&
                                         (sequence_count >=
                                          (sequence_delay - 8'd1))) begin
                                sequence_count <= 8'h00;
                                timeout_count  <= 8'h00;
                                current_state  <= ST_RUN;
                            end else if (timer_tick_ce &&
                                         (sequence_count != 8'hff)) begin
                                sequence_count <= sequence_count + 8'd1;
                            end
                        end else begin
                            sequence_count <= 8'h00;
                            if ((startup_timeout != 8'd0) && timer_tick_ce) begin
                                if (timeout_count >=
                                    (startup_timeout - 8'd1)) begin
                                    fault_strobe  <= 1'b1;
                                    fault_code    <= FAULT_STARTUP_TIMEOUT;
                                    fault_detail  <= 3'd4;
                                    timeout_count <= 8'h00;
                                end else if (timeout_count != 8'hff) begin
                                    timeout_count <= timeout_count + 8'd1;
                                end
                            end
                        end
                    end

                    ST_RUN: begin
                        rail_en        <= 4'b1111;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        if (!system_request) begin
                            current_state <= ST_SHUTDOWN_R4;
                        end else if (!pg_good[0]) begin
                            fault_strobe <= 1'b1;
                            fault_code   <= FAULT_PG1;
                            fault_detail <= 3'd1;
                        end else if (!pg_good[1]) begin
                            fault_strobe <= 1'b1;
                            fault_code   <= FAULT_PG2;
                            fault_detail <= 3'd2;
                        end else if (!pg_good[2]) begin
                            fault_strobe <= 1'b1;
                            fault_code   <= FAULT_PG3;
                            fault_detail <= 3'd3;
                        end else if (!pg_good[3]) begin
                            fault_strobe <= 1'b1;
                            fault_code   <= FAULT_PG4;
                            fault_detail <= 3'd4;
                        end
                    end

                    ST_SHUTDOWN_R4: begin
                        rail_en <= 4'b0111;
                        if (sequence_delay == 8'd0) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R3;
                        end else if (timer_tick_ce &&
                                     (sequence_count >=
                                      (sequence_delay - 8'd1))) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R3;
                        end else if (timer_tick_ce &&
                                     (sequence_count != 8'hff)) begin
                            sequence_count <= sequence_count + 8'd1;
                        end
                    end

                    ST_SHUTDOWN_R3: begin
                        rail_en <= 4'b0011;
                        if (sequence_delay == 8'd0) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R2;
                        end else if (timer_tick_ce &&
                                     (sequence_count >=
                                      (sequence_delay - 8'd1))) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R2;
                        end else if (timer_tick_ce &&
                                     (sequence_count != 8'hff)) begin
                            sequence_count <= sequence_count + 8'd1;
                        end
                    end

                    ST_SHUTDOWN_R2: begin
                        rail_en <= 4'b0001;
                        if (sequence_delay == 8'd0) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R1;
                        end else if (timer_tick_ce &&
                                     (sequence_count >=
                                      (sequence_delay - 8'd1))) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_SHUTDOWN_R1;
                        end else if (timer_tick_ce &&
                                     (sequence_count != 8'hff)) begin
                            sequence_count <= sequence_count + 8'd1;
                        end
                    end

                    ST_SHUTDOWN_R1: begin
                        rail_en <= 4'b0000;
                        if (sequence_delay == 8'd0) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_OFF;
                        end else if (timer_tick_ce &&
                                     (sequence_count >=
                                      (sequence_delay - 8'd1))) begin
                            sequence_count <= 8'h00;
                            current_state  <= ST_OFF;
                        end else if (timer_tick_ce &&
                                     (sequence_count != 8'hff)) begin
                            sequence_count <= sequence_count + 8'd1;
                        end
                    end

                    ST_FAULT: begin
                        rail_en        <= 4'b0000;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        current_state  <= ST_OFF;
                    end

                    default: begin
                        rail_en        <= 4'b0000;
                        sequence_count <= 8'h00;
                        timeout_count  <= 8'h00;
                        current_state  <= ST_OFF;
                    end
                endcase
            end
        end
    end

endmodule

`default_nettype wire
