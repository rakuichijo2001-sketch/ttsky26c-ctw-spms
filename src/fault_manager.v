/* CTW-SPMS deterministic critical-fault arbitration. */

`default_nettype none

module fault_manager (
    input  wire       overcurrent_fault,
    input  wire       overtemp_fault,
    input  wire       power_anomaly_fault,
    input  wire       watchdog_timeout_fault,
    input  wire       rail_fault_strobe,
    input  wire [3:0] rail_fault_code,
    input  wire [2:0] rail_fault_detail,
    output reg        fault_valid,
    output reg  [3:0] fault_code,
    output reg  [2:0] fault_detail
);

    localparam [3:0] FAULT_OVERCURRENT      = 4'h6;
    localparam [3:0] FAULT_OVERTEMP         = 4'h7;
    localparam [3:0] FAULT_POWER_ANOMALY    = 4'h8;
    localparam [3:0] FAULT_WATCHDOG_TIMEOUT = 4'h9;

    always @* begin
        fault_valid  = 1'b0;
        fault_code   = 4'h0;
        fault_detail = 3'd0;

        /* Frozen priority: OT, OC, anomaly, startup/PG, watchdog. */
        if (overtemp_fault) begin
            fault_valid = 1'b1;
            fault_code  = FAULT_OVERTEMP;
        end else if (overcurrent_fault) begin
            fault_valid = 1'b1;
            fault_code  = FAULT_OVERCURRENT;
        end else if (power_anomaly_fault) begin
            fault_valid = 1'b1;
            fault_code  = FAULT_POWER_ANOMALY;
        end else if (rail_fault_strobe) begin
            fault_valid  = 1'b1;
            fault_code   = rail_fault_code;
            fault_detail = rail_fault_detail;
        end else if (watchdog_timeout_fault) begin
            fault_valid = 1'b1;
            fault_code  = FAULT_WATCHDOG_TIMEOUT;
        end
    end

endmodule

`default_nettype wire
