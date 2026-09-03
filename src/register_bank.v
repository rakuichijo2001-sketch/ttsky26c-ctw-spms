/* CTW-SPMS authoritative byte-wide programmable register bank. */

`default_nettype none

module register_bank (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       write_strobe,
    input  wire [6:0] write_addr,
    input  wire [7:0] write_data,
    input  wire [6:0] read_addr,
    output reg  [7:0] read_data,

    output reg  [7:0] power_sample,
    output reg        power_sample_strobe,
    output reg  [7:0] power_nominal,
    output reg  [7:0] anomaly_warn_threshold,
    output reg  [7:0] anomaly_fault_threshold,
    output reg  [7:0] power_high_threshold,
    output reg  [7:0] power_med_threshold,
    output reg  [7:0] power_low_threshold,
    output reg  [7:0] pg_stable_count,
    output reg  [7:0] sequence_delay,
    output reg  [7:0] startup_timeout,
    output reg  [7:0] watchdog_timeout,
    output reg  [7:0] retry_delay,
    output reg  [7:0] max_retry,
    output reg        system_enable,
    output reg        force_shutdown,
    output reg        watchdog_enable,
    output reg        clear_fault_pulse,
    output reg  [7:0] warn_persist_count,
    output reg  [7:0] fault_persist_count,

    input  wire [7:0] status,
    input  wire [7:0] filtered_sample,
    input  wire [7:0] power_deviation_value,
    input  wire [1:0] power_level,
    input  wire [3:0] pg_status,
    input  wire [3:0] rail_status,
    input  wire [2:0] load_status,
    input  wire [3:0] last_fault,
    input  wire [7:0] fault_count,
    input  wire [7:0] retry_count,
    input  wire [4:0] current_state,
    input  wire [2:0] fault_detail
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            power_sample             <= 8'h00;
            power_sample_strobe      <= 1'b0;
            power_nominal            <= 8'h80;
            anomaly_warn_threshold   <= 8'h10;
            anomaly_fault_threshold  <= 8'h20;
            power_high_threshold     <= 8'hc0;
            power_med_threshold      <= 8'h80;
            power_low_threshold      <= 8'h40;
            pg_stable_count          <= 8'h03;
            sequence_delay           <= 8'h05;
            startup_timeout          <= 8'h64;
            watchdog_timeout         <= 8'h64;
            retry_delay              <= 8'h32;
            max_retry                <= 8'h03;
            system_enable            <= 1'b0;
            force_shutdown           <= 1'b0;
            watchdog_enable          <= 1'b0;
            clear_fault_pulse        <= 1'b0;
            warn_persist_count       <= 8'h02;
            fault_persist_count      <= 8'h03;
        end else begin
            power_sample_strobe <= 1'b0;
            clear_fault_pulse <= 1'b0;
            if (write_strobe) begin
                case (write_addr)
                    7'h00: begin
                        power_sample        <= write_data;
                        power_sample_strobe <= 1'b1;
                    end
                    7'h01: power_nominal           <= write_data;
                    7'h02: anomaly_warn_threshold  <= write_data;
                    7'h03: anomaly_fault_threshold <= write_data;
                    7'h04: power_high_threshold    <= write_data;
                    7'h05: power_med_threshold     <= write_data;
                    7'h06: power_low_threshold     <= write_data;
                    7'h07: pg_stable_count         <= write_data;
                    7'h08: sequence_delay          <= write_data;
                    7'h09: startup_timeout         <= write_data;
                    7'h0a: watchdog_timeout        <= write_data;
                    7'h0b: retry_delay             <= write_data;
                    7'h0c: max_retry               <= write_data;
                    7'h0d: begin
                        system_enable     <= write_data[0];
                        clear_fault_pulse <= write_data[1];
                        force_shutdown    <= write_data[2];
                        watchdog_enable   <= write_data[3];
                    end
                    7'h0e: warn_persist_count      <= write_data;
                    7'h0f: fault_persist_count     <= write_data;
                    default: begin end
                endcase
            end
        end
    end

    always @* begin
        case (read_addr)
            7'h00: read_data = power_sample;
            7'h01: read_data = power_nominal;
            7'h02: read_data = anomaly_warn_threshold;
            7'h03: read_data = anomaly_fault_threshold;
            7'h04: read_data = power_high_threshold;
            7'h05: read_data = power_med_threshold;
            7'h06: read_data = power_low_threshold;
            7'h07: read_data = pg_stable_count;
            7'h08: read_data = sequence_delay;
            7'h09: read_data = startup_timeout;
            7'h0a: read_data = watchdog_timeout;
            7'h0b: read_data = retry_delay;
            7'h0c: read_data = max_retry;
            7'h0d: read_data = {4'b0000, watchdog_enable,
                                force_shutdown, 1'b0, system_enable};
            7'h0e: read_data = warn_persist_count;
            7'h0f: read_data = fault_persist_count;
            7'h10: read_data = status;
            7'h11: read_data = filtered_sample;
            7'h12: read_data = power_deviation_value;
            7'h13: read_data = {6'b000000, power_level};
            7'h14: read_data = {4'b0000, pg_status};
            7'h15: read_data = {4'b0000, rail_status};
            7'h16: read_data = {5'b00000, load_status};
            7'h17: read_data = {4'b0000, last_fault};
            7'h18: read_data = fault_count;
            7'h19: read_data = retry_count;
            7'h1a: read_data = {3'b000, current_state};
            7'h1b: read_data = {5'b00000, fault_detail};
            7'h1f: read_data = 8'h01;
            default: read_data = 8'h00;
        endcase
    end

endmodule

`default_nettype wire
