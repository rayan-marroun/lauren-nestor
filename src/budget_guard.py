"""Soft, in-process budget tracking.

This is NOT the real safety net -- that's the GCP Budget alert wired to a
Cloud Function that force-stops the VM (see deploy/budget_alert_function).
This module exists so the loop can wind down gracefully -- log a summary,
leave the workspace in a clean state -- instead of just getting killed
mid-thought when the hard stop hits.
"""
import os
import time

STARTED_AT_PATH = "/opt/lauren/started_at.txt"


class BudgetExceeded(Exception):
    pass


class BudgetGuard:
    def __init__(self):
        self.cap_eur = float(os.environ.get("BUDGET_EUR_CAP", "235"))
        self.hourly_eur = float(os.environ.get("HOURLY_COST_ESTIMATE_EUR", "0.35"))
        self.soft_fraction = float(os.environ.get("BUDGET_SOFT_STOP_FRACTION", "0.8"))
        self.started_at = self._load_or_init_started_at()

    def _load_or_init_started_at(self) -> float:
        # Persisted so a crash-and-restart doesn't silently reset spend
        # tracking to zero -- the VM (and its cost) has been running the
        # whole time regardless of whether this process stayed up.
        if os.path.exists(STARTED_AT_PATH):
            with open(STARTED_AT_PATH, "r", encoding="utf-8") as f:
                return float(f.read().strip())
        now = time.time()
        with open(STARTED_AT_PATH, "w", encoding="utf-8") as f:
            f.write(str(now))
        return now

    def elapsed_hours(self) -> float:
        return (time.time() - self.started_at) / 3600.0

    def estimated_spend_eur(self) -> float:
        return self.elapsed_hours() * self.hourly_eur

    def soft_cap_eur(self) -> float:
        return self.cap_eur * self.soft_fraction

    def check(self) -> None:
        spend = self.estimated_spend_eur()
        if spend >= self.soft_cap_eur():
            raise BudgetExceeded(
                f"Estimated spend EUR{spend:.2f} has reached the soft cap "
                f"EUR{self.soft_cap_eur():.2f} ({self.soft_fraction:.0%} of "
                f"EUR{self.cap_eur:.2f}). Wrapping up."
            )

    def status_line(self) -> str:
        return (
            f"~EUR{self.estimated_spend_eur():.2f} spent of EUR{self.cap_eur:.2f} "
            f"cap ({self.elapsed_hours():.1f}h runtime)"
        )
