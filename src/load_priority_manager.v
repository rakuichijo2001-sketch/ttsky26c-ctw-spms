/* CTW-SPMS three-load shedding and staged restoration manager. */

`default_nettype none

module load_priority_manager (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       system_run,
    input  wire       hard_shutdown,
    input  wire [1:0] power_level,
    input  wire [7:0] restore_delay,
    output reg  [2:0] load_en
);

    reg [2:0] target_loads;
    reg [7:0] restore_count;

    always @* begin
        case (power_level)
            2'b11: target_loads = 3'b111;
            2'b10: target_loads = 3'b011;
            2'b01: target_loads = 3'b001;
            default: target_loads = 3'b000;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            load_en       <= 3'b000;
            restore_count <= 8'h00;
        end else if (hard_shutdown || !system_run) begin
            load_en       <= 3'b000;
            restore_count <= 8'h00;
        end else if (target_loads < load_en) begin
            /* Shedding is prompt and may remove multiple lower priorities. */
            load_en       <= target_loads;
            restore_count <= 8'h00;
        end else if (target_loads > load_en) begin
            if ((restore_delay == 8'd0) ||
                (restore_count >= (restore_delay - 8'd1))) begin
                restore_count <= 8'h00;
                if (!load_en[0] && target_loads[0]) begin
                    load_en[0] <= 1'b1;
                end else if (!load_en[1] && target_loads[1]) begin
                    load_en[1] <= 1'b1;
                end else if (!load_en[2] && target_loads[2]) begin
                    load_en[2] <= 1'b1;
                end
            end else begin
                restore_count <= restore_count + 8'd1;
            end
        end else begin
            restore_count <= 8'h00;
        end
    end

endmodule

`default_nettype wire
