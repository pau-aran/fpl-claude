"""Console I/O compatibility — make our CLIs printable on a Windows terminal.

Every module here writes football prose: transfers read `Mbeumo → Rice`, chip
gates read `net ≥ threshold`, errors read `−2.72`. Those are U+2192, U+2265 and
U+2212 — none of which exist in cp1252, the default console encoding on the
owner's Windows machine. Printing one raises UnicodeEncodeError and takes the
whole run down *after* the work is finished, which is the worst possible time:
the calibration is computed, the gameweek is scored, and the process dies on
the way out.

File writes were never the problem (we pass encoding="utf-8" explicitly). This
is stdout/stderr only, so the fix belongs at the CLI boundary: call
`enable_utf8_output()` first thing in main(), before anything prints.

No-op on POSIX, where the streams are already UTF-8.
"""

from __future__ import annotations

import sys


def enable_utf8_output() -> None:
    """Reconfigure stdout/stderr to UTF-8 so non-ASCII output cannot crash a CLI.

    `errors="replace"` rather than "strict": a console that genuinely cannot
    render an arrow should print a placeholder, not abort a scored gameweek.
    Streams that are redirected, wrapped or already UTF-8 are left alone.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # a StringIO or similar under test capture
            continue
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding in ("utf8", "utf8mb4"):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # detached or non-reconfigurable stream
            pass
