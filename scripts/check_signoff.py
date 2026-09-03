#!/usr/bin/env python3
"""Enforce the bounded CTW-SPMS post-route signoff policy.

This gate deliberately does not alter signoff constraints or reports. It
requires all hard physical/timing checks to be clean and permits only the
documented, tightly bounded max-transition exception.
"""

from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


MAX_SLEW_PINS = 2
MAX_SLEW_OVERSHOOT_PCT = 5.0
EXPECTED_CORNERS = {
    f"{rc}_{pvt}"
    for rc in ("min", "nom", "max")
    for pvt in ("ff_n40C_1v95", "tt_025C_1v80", "ss_100C_1v60")
}

ZERO_METRICS = (
    "magic__drc_error__count",
    "route__drc_errors",
    "antenna__violating__nets",
    "antenna__violating__pins",
    "design__lvs_error__count",
    "design__lvs_device_difference__count",
    "design__lvs_net_difference__count",
    "design__lvs_property_fail__count",
    "design__lvs_unmatched_device__count",
    "design__lvs_unmatched_net__count",
    "design__lvs_unmatched_pin__count",
    "timing__setup_vio__count",
    "timing__hold_vio__count",
    "timing__setup__tns",
    "timing__hold__tns",
    "design__max_cap_violation__count",
    "design__max_fanout_violation__count",
)

PER_CORNER_ZERO_METRICS = (
    "timing__setup_vio__count",
    "timing__hold_vio__count",
    "timing__setup__tns",
    "timing__hold__tns",
    "design__max_cap_violation__count",
    "design__max_fanout_violation__count",
)

NONNEGATIVE_METRICS = (
    "timing__setup__ws",
    "timing__hold__ws",
)

VIOLATION_RE = re.compile(
    r"^\s*(?P<pin>\S+)\s+"
    r"(?P<limit>\d+(?:\.\d+)?)\s+"
    r"(?P<slew>\d+(?:\.\d+)?)\s+"
    r"(?P<slack>-\d+(?:\.\d+)?)\s+\(VIOLATED\)\s*$"
)


class SignoffError(RuntimeError):
    """A release-blocking signoff-policy failure."""


@dataclass(frozen=True)
class SlewViolation:
    corner: str
    pin: str
    limit_ns: float
    slew_ns: float

    @property
    def overshoot_pct(self) -> float:
        return 100.0 * (self.slew_ns - self.limit_ns) / self.limit_ns


def require_zero(metrics: dict[str, object], key: str) -> None:
    if key not in metrics:
        raise SignoffError(f"required metric is missing: {key}")
    try:
        value = float(metrics[key])
    except (TypeError, ValueError) as exc:
        raise SignoffError(f"metric is not numeric: {key}={metrics[key]!r}") from exc
    if not math.isfinite(value) or value != 0.0:
        raise SignoffError(f"hard-gate metric is nonzero: {key}={metrics[key]}")


def require_nonnegative(metrics: dict[str, object], key: str) -> None:
    if key not in metrics:
        raise SignoffError(f"required metric is missing: {key}")
    try:
        value = float(metrics[key])
    except (TypeError, ValueError) as exc:
        raise SignoffError(f"metric is not numeric: {key}={metrics[key]!r}") from exc
    if not math.isfinite(value) or value < 0.0:
        raise SignoffError(f"timing slack is negative: {key}={metrics[key]}")


def find_post_route_reports(run_root: Path) -> list[Path]:
    reports = sorted(run_root.glob("**/*openroad-stapostpnr/*/checks.rpt"))
    if not reports:
        raise SignoffError("no post-route checks.rpt files were found")
    corners = {report.parent.name for report in reports}
    missing_corners = sorted(EXPECTED_CORNERS - corners)
    if missing_corners:
        raise SignoffError(
            "post-route reports are missing required corners: "
            + ", ".join(missing_corners)
        )
    return reports


def parse_slew_violations(reports: list[Path]) -> list[SlewViolation]:
    violations: list[SlewViolation] = []
    for report in reports:
        corner = report.parent.name
        in_max_slew = False
        for line in report.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip().lower()
            if stripped == "max slew":
                in_max_slew = True
                continue
            if in_max_slew and stripped.startswith("max fanout violation count"):
                in_max_slew = False
            if not in_max_slew:
                continue
            match = VIOLATION_RE.match(line)
            if match:
                violations.append(
                    SlewViolation(
                        corner=corner,
                        pin=match.group("pin"),
                        limit_ns=float(match.group("limit")),
                        slew_ns=float(match.group("slew")),
                    )
                )
    return violations


def check(run_root: Path) -> tuple[int, int, float]:
    metrics_path = run_root / "final" / "metrics.json"
    if not metrics_path.is_file():
        raise SignoffError(f"metrics file not found: {metrics_path}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    for key in ZERO_METRICS:
        require_zero(metrics, key)
    for base_key in PER_CORNER_ZERO_METRICS:
        for key in metrics:
            if key.startswith(f"{base_key}__corner:"):
                require_zero(metrics, key)
    for base_key in NONNEGATIVE_METRICS:
        require_nonnegative(metrics, base_key)
        for key in metrics:
            if key.startswith(f"{base_key}__corner:"):
                require_nonnegative(metrics, key)

    try:
        raw_max_slew_pins = float(metrics["design__max_slew_violation__count"])
    except KeyError as exc:
        raise SignoffError(
            "required metric is missing: design__max_slew_violation__count"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise SignoffError("max-slew violation count is not an integer") from exc
    if not raw_max_slew_pins.is_integer():
        raise SignoffError("max-slew violation count is not an integer")
    max_slew_pins = int(raw_max_slew_pins)

    if not 0 <= max_slew_pins <= MAX_SLEW_PINS:
        raise SignoffError(
            f"max-slew pin count {max_slew_pins} exceeds policy limit "
            f"{MAX_SLEW_PINS}"
        )

    reports = find_post_route_reports(run_root)
    violations = parse_slew_violations(reports)
    if max_slew_pins == 0 and violations:
        raise SignoffError("reports contain max-slew violations but metrics count is zero")
    if max_slew_pins > 0 and not violations:
        raise SignoffError("metrics report max-slew violations but no report rows were parsed")

    unique_pins = {violation.pin for violation in violations}
    if len(unique_pins) != max_slew_pins:
        raise SignoffError(
            f"metrics report {max_slew_pins} max-slew pins but reports contain "
            f"{len(unique_pins)} unique pins"
        )
    if len(unique_pins) > MAX_SLEW_PINS:
        raise SignoffError(
            f"reports contain {len(unique_pins)} unique max-slew pins; "
            f"policy permits {MAX_SLEW_PINS}"
        )

    worst_pct = max((violation.overshoot_pct for violation in violations), default=0.0)
    if worst_pct > MAX_SLEW_OVERSHOOT_PCT + 1e-9:
        worst = max(violations, key=lambda violation: violation.overshoot_pct)
        raise SignoffError(
            f"worst max-slew overshoot is {worst_pct:.4f}% at "
            f"{worst.corner}:{worst.pin}; policy limit is "
            f"{MAX_SLEW_OVERSHOOT_PCT:.4f}%"
        )

    return max_slew_pins, len({v.corner for v in violations}), worst_pct


def main() -> int:
    run_root = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/wokwi")
    try:
        pin_count, corner_count, worst_pct = check(run_root)
    except (OSError, json.JSONDecodeError, SignoffError) as exc:
        print(f"SIGNOFF FAIL: {exc}", file=sys.stderr)
        return 1

    print("SIGNOFF PASS: all hard-gate metrics are clean")
    print(
        "SIGNOFF PASS: max slew "
        f"{pin_count}/{MAX_SLEW_PINS} pins, "
        f"{corner_count} affected corners, "
        f"worst overshoot {worst_pct:.4f}/{MAX_SLEW_OVERSHOOT_PCT:.4f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
