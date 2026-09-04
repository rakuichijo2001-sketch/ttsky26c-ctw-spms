/*
 * CTW-SPMS — Programmable Smart Power Management & Supervisor
 * Tiny Tapeout TTSKY26c / SKY130 top-level integration.
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_ctw_spms (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    localparam [4:0] ST_RUN = 5'd9;

    wire core_rst_n;

    wire pg1_sync;
    wire pg2_sync;
    wire pg3_sync;
    wire pg4_sync;
    wire overcurrent_sync;
    wire overtemp_sync;
    wire watchdog_sync;
    wire force_shutdown_ext_sync;
    wire ena_sync;
    wire timer_tick_ce;

    wire spi_miso;
    wire [6:0] spi_read_addr;
    wire [7:0] spi_read_data;
    wire [6:0] spi_write_addr;
    wire [7:0] spi_write_data;
    wire [1:0] spi_write_data_23_copy_a;
    wire [1:0] spi_write_data_23_copy_b;
    wire [1:0] spi_write_data_23_copy_c;
    wire       spi_write_strobe;

    wire [7:0] power_sample;
    wire       power_sample_strobe;
    wire [7:0] power_nominal;
    wire [7:0] anomaly_warn_threshold;
    wire [7:0] anomaly_fault_threshold;
    wire [7:0] power_high_threshold;
    wire [7:0] power_med_threshold;
    wire [7:0] power_low_threshold;
    wire [7:0] pg_stable_count;
    wire [7:0] sequence_delay;
    wire [7:0] startup_timeout;
    wire [7:0] watchdog_timeout;
    wire [7:0] retry_delay;
    wire [7:0] max_retry;
    wire       system_enable;
    wire       force_shutdown;
    wire       watchdog_enable;
    wire       clear_fault_pulse;
    wire [7:0] warn_persist_count;
    wire [7:0] fault_persist_count;

    wire [7:0] filtered_sample;
    wire       filtered_valid;
    wire       filtered_strobe;
    wire [7:0] deviation;
    wire       anomaly_warning;
    wire       anomaly_fault;
    wire [1:0] power_level;

    wire [3:0] pg_good;
    wire [3:0] sequencer_rail_en;
    wire [4:0] current_state;
    wire       sequencer_fault_strobe;
    wire [3:0] sequencer_fault_code;
    wire [2:0] sequencer_fault_detail;
    wire       sequencer_run;

    wire [2:0] manager_load_en;
    wire       watchdog_fault;
    wire       fault_event_valid;
    wire [3:0] fault_event_code;
    wire [2:0] fault_event_detail;
    wire       fault_latched;
    wire       fault_lock;
    wire       retry_pulse;
    wire [3:0] last_fault;
    wire [7:0] fault_count;
    wire [7:0] retry_count;
    wire [2:0] last_fault_detail;

    wire force_shutdown_active;
    wire system_request;
    wire hard_fault_override;
    wire safe_shutdown;
    wire [3:0] final_rail_en;
    wire [2:0] final_load_en;
    wire [7:0] status;

    reset_sync u_reset_sync (
        .clk(clk), .async_rst_n(rst_n), .sync_rst_n(core_rst_n)
    );

    sync_2ff u_sync_pg1 (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[0]), .sync_out(pg1_sync));
    sync_2ff u_sync_pg2 (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[1]), .sync_out(pg2_sync));
    sync_2ff u_sync_pg3 (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[2]), .sync_out(pg3_sync));
    sync_2ff u_sync_pg4 (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[3]), .sync_out(pg4_sync));
    sync_2ff u_sync_overcurrent (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[4]), .sync_out(overcurrent_sync));
    sync_2ff u_sync_overtemp (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[5]), .sync_out(overtemp_sync));
    sync_2ff u_sync_watchdog (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[6]), .sync_out(watchdog_sync));
    sync_2ff u_sync_force_shutdown (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ui_in[7]),
                         .sync_out(force_shutdown_ext_sync));
    sync_2ff u_sync_ena (.clk(clk), .rst_n(core_rst_n),
                         .async_in(ena), .sync_out(ena_sync));

    timebase_tick u_timebase_tick (
        .clk(clk), .rst_n(core_rst_n), .timer_tick_ce(timer_tick_ce)
    );

    spi_slave u_spi_slave (
        .clk(clk), .rst_n(core_rst_n),
        .spi_cs_n_async(uio_in[1]), .spi_sclk_async(uio_in[2]),
        .spi_mosi_async(uio_in[3]), .spi_miso(spi_miso),
        .read_addr(spi_read_addr), .read_data(spi_read_data),
        .write_addr(spi_write_addr), .write_data(spi_write_data),
        .write_data_23_copy_a(spi_write_data_23_copy_a),
        .write_data_23_copy_b(spi_write_data_23_copy_b),
        .write_data_23_copy_c(spi_write_data_23_copy_c),
        .write_strobe(spi_write_strobe)
    );

    register_bank u_register_bank (
        .clk(clk), .rst_n(core_rst_n),
        .write_strobe(spi_write_strobe),
        .write_addr(spi_write_addr), .write_data(spi_write_data),
        .write_data_23_copy_a(spi_write_data_23_copy_a),
        .write_data_23_copy_b(spi_write_data_23_copy_b),
        .write_data_23_copy_c(spi_write_data_23_copy_c),
        .read_addr(spi_read_addr), .read_data(spi_read_data),
        .power_sample(power_sample),
        .power_sample_strobe(power_sample_strobe),
        .power_nominal(power_nominal),
        .anomaly_warn_threshold(anomaly_warn_threshold),
        .anomaly_fault_threshold(anomaly_fault_threshold),
        .power_high_threshold(power_high_threshold),
        .power_med_threshold(power_med_threshold),
        .power_low_threshold(power_low_threshold),
        .pg_stable_count(pg_stable_count),
        .sequence_delay(sequence_delay),
        .startup_timeout(startup_timeout),
        .watchdog_timeout(watchdog_timeout),
        .retry_delay(retry_delay), .max_retry(max_retry),
        .system_enable(system_enable), .force_shutdown(force_shutdown),
        .watchdog_enable(watchdog_enable),
        .clear_fault_pulse(clear_fault_pulse),
        .warn_persist_count(warn_persist_count),
        .fault_persist_count(fault_persist_count),
        .status(status), .filtered_sample(filtered_sample),
        .power_deviation_value(deviation), .power_level(power_level),
        .pg_status(pg_good), .rail_status(final_rail_en),
        .load_status(final_load_en), .last_fault(last_fault),
        .fault_count(fault_count), .retry_count(retry_count),
        .current_state(current_state),
        .fault_detail(last_fault_detail)
    );

    power_fir u_power_fir (
        .clk(clk), .rst_n(core_rst_n),
        .sample_strobe(power_sample_strobe), .sample_in(power_sample),
        .filtered_sample(filtered_sample),
        .filtered_valid(filtered_valid),
        .filtered_strobe(filtered_strobe)
    );

    power_deviation u_power_deviation (
        .filtered_sample(filtered_sample), .power_nominal(power_nominal),
        .deviation(deviation)
    );

    anomaly_detector u_anomaly_detector (
        .clk(clk), .rst_n(core_rst_n), .sample_strobe(filtered_strobe),
        .deviation(deviation),
        .warn_threshold(anomaly_warn_threshold),
        .fault_threshold(anomaly_fault_threshold),
        .warn_persist_count(warn_persist_count),
        .fault_persist_count(fault_persist_count),
        .warning_active(anomaly_warning), .fault_active(anomaly_fault)
    );

    power_level_classifier u_power_level_classifier (
        .sample_valid(filtered_valid), .filtered_sample(filtered_sample),
        .high_threshold(power_high_threshold),
        .med_threshold(power_med_threshold),
        .low_threshold(power_low_threshold),
        .power_level(power_level)
    );

    pg_filter u_pg1_filter (.clk(clk), .rst_n(core_rst_n),
                            .timer_tick_ce(timer_tick_ce), .pg_sync(pg1_sync),
                            .stable_count_cfg(pg_stable_count),
                            .pg_good(pg_good[0]));
    pg_filter u_pg2_filter (.clk(clk), .rst_n(core_rst_n),
                            .timer_tick_ce(timer_tick_ce), .pg_sync(pg2_sync),
                            .stable_count_cfg(pg_stable_count),
                            .pg_good(pg_good[1]));
    pg_filter u_pg3_filter (.clk(clk), .rst_n(core_rst_n),
                            .timer_tick_ce(timer_tick_ce), .pg_sync(pg3_sync),
                            .stable_count_cfg(pg_stable_count),
                            .pg_good(pg_good[2]));
    pg_filter u_pg4_filter (.clk(clk), .rst_n(core_rst_n),
                            .timer_tick_ce(timer_tick_ce), .pg_sync(pg4_sync),
                            .stable_count_cfg(pg_stable_count),
                            .pg_good(pg_good[3]));

    assign force_shutdown_active = force_shutdown | force_shutdown_ext_sync;
    assign system_request = ena_sync & system_enable & ~force_shutdown_active;
    assign sequencer_run = (current_state == ST_RUN);

    rail_sequencer u_rail_sequencer (
        .clk(clk), .rst_n(core_rst_n), .timer_tick_ce(timer_tick_ce),
        .system_request(system_request),
        .fault_shutdown(hard_fault_override), .pg_good(pg_good),
        .sequence_delay(sequence_delay), .startup_timeout(startup_timeout),
        .rail_en(sequencer_rail_en), .current_state(current_state),
        .fault_strobe(sequencer_fault_strobe),
        .fault_code(sequencer_fault_code),
        .fault_detail(sequencer_fault_detail)
    );

    watchdog u_watchdog (
        .clk(clk), .rst_n(core_rst_n), .timer_tick_ce(timer_tick_ce),
        .enable(watchdog_enable & sequencer_run & ~fault_latched),
        .heartbeat(watchdog_sync), .timeout_cfg(watchdog_timeout),
        .timeout_fault(watchdog_fault)
    );

    fault_manager u_fault_manager (
        .overcurrent_fault(overcurrent_sync),
        .overtemp_fault(overtemp_sync),
        .power_anomaly_fault(anomaly_fault & system_request),
        .watchdog_timeout_fault(watchdog_fault),
        .rail_fault_strobe(sequencer_fault_strobe),
        .rail_fault_code(sequencer_fault_code),
        .rail_fault_detail(sequencer_fault_detail),
        .fault_valid(fault_event_valid), .fault_code(fault_event_code),
        .fault_detail(fault_event_detail)
    );

    fault_controller u_fault_controller (
        .clk(clk), .rst_n(core_rst_n), .timer_tick_ce(timer_tick_ce),
        .system_request(system_request), .sequencer_run(sequencer_run),
        .clear_fault(clear_fault_pulse), .fault_valid(fault_event_valid),
        .fault_code(fault_event_code), .fault_detail(fault_event_detail),
        .retry_delay(retry_delay), .max_retry(max_retry),
        .fault_latched(fault_latched), .fault_lock(fault_lock),
        .retry_pulse(retry_pulse), .last_fault(last_fault),
        .fault_count(fault_count), .retry_count(retry_count),
        .last_fault_detail(last_fault_detail)
    );

    assign hard_fault_override = fault_event_valid | fault_latched | fault_lock;
    assign safe_shutdown = hard_fault_override | force_shutdown_active |
                           ~ena_sync | ~rst_n;

    load_priority_manager u_load_priority_manager (
        .clk(clk), .rst_n(core_rst_n), .timer_tick_ce(timer_tick_ce),
        .system_run(sequencer_run & system_request),
        .hard_shutdown(safe_shutdown), .power_level(power_level),
        .restore_delay(sequence_delay), .load_en(manager_load_en)
    );

    output_safety u_output_safety (
        .safe_shutdown(safe_shutdown),
        .sequencer_rail_en(sequencer_rail_en),
        .manager_load_en(manager_load_en),
        .final_rail_en(final_rail_en), .final_load_en(final_load_en)
    );

    assign status = {ena_sync, watchdog_enable, force_shutdown_active,
                     fault_lock, fault_latched, anomaly_warning,
                     sequencer_run, system_enable};

    assign uo_out  = {hard_fault_override, final_load_en, final_rail_en};
    assign uio_out = {7'b0000000, spi_miso};
    assign uio_oe  = 8'b00000001;

    /* uio[7:4] and uio[0] are intentionally unused inputs. */
    wire _unused = &{1'b0, retry_pulse, uio_in[7:4], uio_in[0]};

endmodule

`default_nettype wire
