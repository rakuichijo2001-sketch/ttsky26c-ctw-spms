/*
 * CTW-SPMS SPI slave
 *
 * SPI Mode 0, MSB first, 16 clocks per transaction.
 * All protocol state runs in the 10 MHz core clock domain. External SPI
 * signals are synchronized before edge detection; SPI_SCLK is never used as
 * an RTL clock.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module spi_slave (
    input  wire       clk,
    input  wire       rst_n,

    input  wire       spi_cs_n_async,
    input  wire       spi_sclk_async,
    input  wire       spi_mosi_async,
    output wire       spi_miso,

    output reg  [6:0] read_addr,
    input  wire [7:0] read_data,

    output reg  [6:0] write_addr,
    output reg  [7:0] write_data,
    output reg        write_strobe
);

    wire spi_cs_n_sync;
    wire spi_sclk_sync;
    wire spi_mosi_sync;

    reg        spi_sclk_sync_d;
    /*
     * Four-bit Johnson phase counter: eight positions with shift/invert
     * next-state paths.  This avoids both the binary carry path that was
     * marginal after routing and the area/congestion cost of an eight-bit
     * one-hot counter.
     */
    reg  [3:0] bit_phase;
    reg        second_byte;
    reg  [6:0] rx_shift;
    reg  [6:0] tx_shift;
    reg  [6:0] frame_addr;
    reg        read_frame;
    reg        frame_done;
    reg        read_load_pending;
    reg        miso_reg;

    wire       sclk_rise;
    wire       phase_last;
    wire [7:0] rx_byte_next;

    sync_2ff #(
        .RESET_VALUE (1'b1)
    ) u_sync_spi_cs_n (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (spi_cs_n_async),
        .sync_out (spi_cs_n_sync)
    );

    sync_2ff u_sync_spi_sclk (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (spi_sclk_async),
        .sync_out (spi_sclk_sync)
    );

    sync_2ff u_sync_spi_mosi (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (spi_mosi_async),
        .sync_out (spi_mosi_sync)
    );

    assign sclk_rise = spi_sclk_sync & ~spi_sclk_sync_d;
    assign phase_last = (bit_phase == 4'b1000);
    assign rx_byte_next = {rx_shift, spi_mosi_sync};
    assign spi_miso = miso_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_sclk_sync_d <= 1'b0;
            bit_phase       <= 4'b0000;
            second_byte     <= 1'b0;
            rx_shift        <= 7'd0;
            tx_shift        <= 7'd0;
            frame_addr      <= 7'd0;
            read_frame      <= 1'b0;
            frame_done      <= 1'b0;
            read_load_pending <= 1'b0;
            miso_reg        <= 1'b0;
            read_addr       <= 7'd0;
            write_addr      <= 7'd0;
            write_data      <= 8'd0;
            write_strobe    <= 1'b0;
        end else begin
            spi_sclk_sync_d <= spi_sclk_sync;
            write_strobe    <= 1'b0;

            if (read_load_pending) begin
                tx_shift          <= read_data[6:0];
                miso_reg          <= read_data[7];
                read_load_pending <= 1'b0;
            end

            if (spi_cs_n_sync) begin
                bit_phase    <= 4'b0000;
                second_byte  <= 1'b0;
                rx_shift   <= 7'd0;
                tx_shift   <= 7'd0;
                frame_addr <= 7'd0;
                read_frame <= 1'b0;
                frame_done <= 1'b0;
                read_load_pending <= 1'b0;
                miso_reg   <= 1'b0;
            end else if (!frame_done && sclk_rise) begin
                rx_shift <= rx_byte_next[6:0];

                if (!second_byte && phase_last) begin
                    /* First byte: R/W in bit7, address in bits6:0. */
                    frame_addr <= rx_byte_next[6:0];
                    read_frame <= rx_byte_next[7];
                    second_byte <= 1'b1;
                    if (rx_byte_next[7]) begin
                        read_addr         <= rx_byte_next[6:0];
                        read_load_pending <= 1'b1;
                    end else begin
                        tx_shift <= 7'd0;
                        miso_reg <= 1'b0;
                    end
                end else if (second_byte) begin
                    if (read_frame) begin
                        /*
                         * The master sampled the current MISO bit on this
                         * external rising edge. Prepare the next bit now.
                         * This avoids relying on a delayed synchronized
                         * falling edge at the specified 2 MHz maximum SCLK.
                         */
                        if (!phase_last) begin
                            miso_reg <= tx_shift[6];
                            tx_shift <= {tx_shift[5:0], 1'b0};
                        end else begin
                            miso_reg   <= 1'b0;
                            frame_done <= 1'b1;
                        end
                    end else if (phase_last) begin
                        /* Commit a write only after all sixteen clocks. */
                        write_addr <= frame_addr;
                        write_data <= rx_byte_next;
                        write_strobe <= 1'b1;
                        frame_done <= 1'b1;
                        miso_reg   <= 1'b0;
                    end
                end

                bit_phase <= {bit_phase[2:0], ~bit_phase[3]};
            end
        end
    end

endmodule

`default_nettype wire
