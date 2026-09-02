/* CTW-SPMS final fail-safe output override. */

`default_nettype none

module output_safety (
    input  wire       safe_shutdown,
    input  wire [3:0] sequencer_rail_en,
    input  wire [2:0] manager_load_en,
    output wire [3:0] final_rail_en,
    output wire [2:0] final_load_en
);

    assign final_rail_en = safe_shutdown ? 4'b0000 : sequencer_rail_en;
    assign final_load_en = safe_shutdown ? 3'b000 : manager_load_en;

endmodule

`default_nettype wire
