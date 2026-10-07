"""Error types and exit codes for the audit verdicts.

EXIT_CONSISTENT means the measured false positive rate is consistent with the
nominal alpha and the trials were enough to say so. EXIT_INFLATED means the
procedure's measured rate excludes the nominal alpha from below: the tool did
its job and the answer is that this procedure lies. EXIT_INCONCLUSIVE means
the exact interval contains alpha but is too wide to rule out a doubled
rate, so the honest output is "run more trials", stated as its own
machine-readable outcome. EXIT_ERROR means the tool failed to answer.
"""

from __future__ import annotations

EXIT_CONSISTENT = 0
EXIT_INFLATED = 1
EXIT_INCONCLUSIVE = 2
EXIT_ERROR = 3


class AuditError(Exception):
    """Base error. Maps to EXIT_ERROR at the CLI boundary."""


class UsageError(AuditError):
    """The caller asked for something invalid; refused before any work starts."""
