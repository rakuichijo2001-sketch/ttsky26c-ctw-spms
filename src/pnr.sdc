# Start from LibreLane's generated constraints, including the 100 ns clock and
# Tiny Tapeout interface delays from src/config.json.
source $::env(FALLBACK_SDC)

# PnR-only guard band: repair trees at fanout 7 so a post-route antenna diode
# can be added without exceeding the signoff MAX_FANOUT_CONSTRAINT of 8.
# Signoff uses its independent fallback SDC and therefore still checks fanout 8.
set_max_fanout 7 [current_design]
