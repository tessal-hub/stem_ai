"""
Shared worker lifecycle contract for logic workers.

Contract enforced in Phase 3:
- Standard completion signal: sig_finished(bool success, str message)
- Standard error signal: sig_error(str message)
- Optional progress signal: sig_progress(int value)
- Cooperative cancellation via stop()/cancel() flag checks
- Exceptions are caught in run() and emitted via sig_error + sig_finished(False, ...)

Notes:
- Domain-specific signals are allowed (for example, serial data streams),
  but lifecycle/error channels must follow the standardized names above.
"""

from __future__ import annotations

WorkerFinishedPayload = tuple[bool, str]
