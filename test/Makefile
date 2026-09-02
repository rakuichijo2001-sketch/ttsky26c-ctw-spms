# CTW-SPMS Cocotb Makefile

SIM ?= icarus
FST ?= -fst

TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../src

PROJECT_SOURCES = sync_2ff.v timebase_tick.v spi_slave.v tt_um_ctw_spms.v

ifneq ($(GATES),yes)

# RTL simulation
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

# Gate-level simulation
SIM_BUILD = sim_build/gl

COMPILE_ARGS += -DGL_TEST
COMPILE_ARGS += -DFUNCTIONAL
COMPILE_ARGS += -DUSE_POWER_PINS
COMPILE_ARGS += -DSIM
COMPILE_ARGS += -DUNIT_DELAY=\#1

VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

# Copied in by Tiny Tapeout GDS workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

COMPILE_ARGS += -I$(SRC_DIR)

VERILOG_SOURCES += $(PWD)/tb.v

TOPLEVEL = tb

COCOTB_TEST_MODULES = test

include $(shell cocotb-config --makefiles)/Makefile.sim
