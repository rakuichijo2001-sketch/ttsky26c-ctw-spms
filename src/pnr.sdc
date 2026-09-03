# CTW-SPMS PnR-only constraints.
#
# Keep the Tiny Tapeout/LibreLane base constraints, then over-constrain only
# the single SPI next-state net that is marginal after routed slow-corner STA.
# Signoff intentionally continues to use the normal 0.750 ns transition limit.

source $::env(FALLBACK_SDC)

# With DESIGN_REPAIR_MAX_SLEW_PCT=50, 0.20 ns here asks RepairDesign for
# roughly 0.10 ns pre-route transition on this one net.  The best baseline
# reached ~0.127 ns pre-route but ~0.785 ns after slow-corner extraction, so
# this should trigger a local gate resize/buffer without globally tightening
# the design or excluding an entire standard-cell family.
set_max_transition 0.20 [get_pins {_2967_/Y}]
set_max_transition 0.20 [get_pins {_3337_/D}]
