#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          GUARDIAN PRO — SECURE FILE SYSTEM                   ║
║          Module : login.py  (Target / Defender)              ║
║          Author : Cybersecurity Student                       ║
║          Course : Introduction to Cybersecurity              ║
╚══════════════════════════════════════════════════════════════╝

PURPOSE
───────
Implements a layered login system that demonstrates:
  • Cryptographic password hashing  (SHA-256)
  • Failed-attempt tracking & rate limiting
  • Intrusion detection  (threshold-based)
  • Secure multi-pass file wiping   (DoD-inspired)
  • Persistent audit logging        (ISO 8601 timestamps)

DESIGN PHILOSOPHY
─────────────────
Every function has ONE responsibility. Side-effects are confined
to explicit I/O helpers. This mirrors real production patterns
used in identity-management services.
"""

import hashlib
import os
import time
from datetime import datetime
from typing import Optional

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION  — tweak these to change system behaviour
# ══════════════════════════════════════════════════════════════

# The password whose SHA-256 hash is compared at runtime.
# ⚠ Never ship plaintext passwords in production — store only the hash.
CORRECT_PASSWORD: str = "742"
CORRECT_PASSWORD_HASH: str = hashlib.sha256(CORRECT_PASSWORD.encode()).hexdigest()

# Filesystem paths
PROTECTED_FILE: str = "protected.txt"
LOG_FILE: str       = "access_log.txt"

# Lockout policy
MAX_ATTEMPTS: int   = 3   # Failed logins before self-destruct triggers
DELAY_SECONDS: int  = 2   # Seconds added after each failure (rate-limit)

# DoD-inspired wipe parameters
WIPE_PASSES: int = 3      # Number of random-data overwrite passes

# ══════════════════════════════════════════════════════════════
#  RUNTIME STATE  — module-level globals (reset by initialize)
# ══════════════════════════════════════════════════════════════

failed_attempts: int  = 0
system_locked:   bool = False


# ══════════════════════════════════════════════════════════════
#  TERMINAL COLOURS  (gracefully disabled on unsupported TTYs)
# ══════════════════════════════════════════════════════════════

class Color:
    """ANSI escape helpers. Falls back to plain text if not a TTY."""
    _enabled = os.isatty(1)

    @staticmethod
    def _w(code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if Color._enabled else text

    red    = staticmethod(lambda t: Color._w("91", t))
    green  = staticmethod(lambda t: Color._w("92", t))
    yellow = staticmethod(lambda t: Color._w("93", t))
    cyan   = staticmethod(lambda t: Color._w("96", t))
    bold   = staticmethod(lambda t: Color._w("1",  t))
    dim    = staticmethod(lambda t: Color._w("2",  t))


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def _now() -> str:
    """Return ISO-8601-style timestamp for log entries."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _divider(char: str = "═", width: int = 60) -> str:
    return char * width


def _log(message: str) -> None:
    """
    Append a timestamped entry to the audit log file AND print it.

    Args:
        message: Human-readable event description.
    """
    entry = f"[{_now()}] {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(entry + "\n")
    print(Color.dim(entry))


# ══════════════════════════════════════════════════════════════
#  CORE SUBSYSTEMS
# ══════════════════════════════════════════════════════════════

def initialize_system() -> None:
    """
    Bootstrap the secure file system.

    Resets runtime state and (re)creates the protected file if absent.
    Call this once before any authentication attempts.
    """
    global failed_attempts, system_locked
    failed_attempts = 0
    system_locked   = False

    if not os.path.exists(PROTECTED_FILE):
        _create_protected_file()
        print(Color.green(f"[+] Protected file '{PROTECTED_FILE}' initialised."))
    else:
        print(Color.cyan(f"[*] Protected file '{PROTECTED_FILE}' already present."))


def _create_protected_file() -> None:
    """Write the initial classified content to the protected file."""
    content = "\n".join([
        _divider(),
        "  CLASSIFIED INFORMATION — LEVEL 5 CLEARANCE REQUIRED",
        _divider(),
        "",
        "  Project Codename : GUARDIAN",
        "  Classification   : TOP SECRET / SCI",
        "  Custodian        : Cyber Operations Division",
        "",
        "  This artefact contains active security protocols.",
        "  Unauthorised access will trigger defensive countermeasures.",
        "",
        f"  Emergency Contact : security@guardian.internal",
        f"  File Created      : {_now()}",
        "",
        _divider(),
        "",
    ])
    with open(PROTECTED_FILE, "w", encoding="utf-8") as fh:
        fh.write(content)


def secure_delete(filename: str) -> bool:
    """
    Multi-pass file wiper (DoD 5220.22-M inspired).

    Procedure:
      1. Overwrite with cryptographically random bytes  (WIPE_PASSES times)
      2. Overwrite with null bytes
      3. Unlink (delete) the inode from the filesystem

    Args:
        filename: Path to the file to destroy.

    Returns:
        True on success, False if the file was already absent or deletion failed.
    """
    if not os.path.exists(filename):
        print(Color.yellow(f"[!] '{filename}' not found — may already be gone."))
        return False

    file_size = os.path.getsize(filename)

    print(f"\n{Color.red(_divider('!'))}")
    print(Color.red(Color.bold("  ⚡ INITIATING SECURE FILE DELETION PROTOCOL")))
    print(f"{Color.red(_divider('!'))}\n")

    try:
        # Pass 1–N: random data
        print(f"[*] Phase 1/{WIPE_PASSES + 1} — Writing random data ({WIPE_PASSES} passes)...")
        for pass_num in range(1, WIPE_PASSES + 1):
            with open(filename, "wb") as fh:
                fh.write(os.urandom(file_size))
            print(Color.dim(f"    └─ Pass {pass_num}/{WIPE_PASSES} complete"))
            time.sleep(0.4)

        # Final pass: zeros
        print(f"[*] Phase {WIPE_PASSES + 1}/{WIPE_PASSES + 1} — Writing null bytes...")
        with open(filename, "wb") as fh:
            fh.write(b"\x00" * file_size)
        time.sleep(0.4)

        # Unlink
        os.remove(filename)

        print(Color.green(f"\n[✓] '{filename}' securely erased — data is unrecoverable."))
        _log(f"SECURITY_EVENT — '{filename}' destroyed (intrusion response).")
        return True

    except OSError as exc:
        print(Color.red(f"[ERROR] Deletion failed: {exc}"))
        _log(f"OS_ERROR — Secure deletion of '{filename}' failed: {exc}")
        return False


def check_password(input_password: str) -> bool:
    """
    Core authentication gate with intrusion detection.

    Algorithm:
      1. Reject immediately if system is locked or file is missing.
      2. Hash the input and compare in constant-ish time.
      3. On success  → reset counter, return True.
      4. On failure  → increment counter, apply rate-limit delay.
      5. At threshold → trigger self-destruct, lock system.

    Args:
        input_password: Raw password string from the caller.

    Returns:
        True if authentication succeeded, False otherwise.
    """
    global failed_attempts, system_locked

    # ── Guard clauses ──────────────────────────────────────────
    if system_locked:
        print(Color.red("[!] SYSTEM LOCKED — access permanently denied."))
        return False

    if not os.path.exists(PROTECTED_FILE):
        print(Color.red("[!] CRITICAL — protected file missing. System compromised."))
        system_locked = True
        return False

    # ── Hash comparison ────────────────────────────────────────
    input_hash = hashlib.sha256(input_password.encode()).hexdigest()

    if input_hash == CORRECT_PASSWORD_HASH:
        _on_auth_success()
        return True
    else:
        return _on_auth_failure(input_password)


def _on_auth_success() -> None:
    """Handle a successful authentication event."""
    global failed_attempts
    failed_attempts = 0

    print(f"\n{Color.green(_divider())}")
    print(Color.green(Color.bold("  ✓  ACCESS GRANTED")))
    print(f"{Color.green(_divider())}")
    print(Color.green("[+] Welcome — identity verified."))
    print(Color.green(f"[+] Protected file is intact.\n"))
    _log(f"AUTH_SUCCESS | Failures cleared.")


def _on_auth_failure(attempted: str) -> bool:
    """
    Handle a failed authentication attempt.

    Returns:
        Always False — caller uses this as the authentication result.
    """
    global failed_attempts, system_locked
    failed_attempts += 1
    remaining = MAX_ATTEMPTS - failed_attempts

    print(f"\n{Color.red(_divider())}")
    print(Color.red(Color.bold("  ✗  ACCESS DENIED — Incorrect password")))
    print(f"{Color.red(_divider())}")
    print(Color.red(f"[!] Failed attempts : {failed_attempts}/{MAX_ATTEMPTS}"))
    _log(f"AUTH_FAILURE — Attempted: '{attempted}' | Strike {failed_attempts}/{MAX_ATTEMPTS}")

    if failed_attempts >= MAX_ATTEMPTS:
        _trigger_self_destruct()
    else:
        print(Color.yellow(f"[!] {remaining} attempt(s) remaining before lockdown."))
        print(Color.dim(f"[*] Rate-limit delay: {DELAY_SECONDS}s…"))
        print(f"{Color.red(_divider())}\n")
        time.sleep(DELAY_SECONDS)

    return False


def _trigger_self_destruct() -> None:
    """Execute the self-destruct sequence on intrusion detection."""
    global system_locked

    print(f"\n{Color.red(_divider('!'))}")
    print(Color.red(Color.bold("  ⚠  UNAUTHORISED ACCESS DETECTED")))
    print(Color.red(f"     Maximum failures ({MAX_ATTEMPTS}) exceeded."))
    print(Color.red("     Activating defensive countermeasures…"))
    print(f"{Color.red(_divider('!'))}\n")
    _log("INTRUSION_DETECTED — Self-destruct sequence initiated.")

    time.sleep(1)
    secure_delete(PROTECTED_FILE)
    system_locked = True
    print(Color.red("[!] System is now permanently locked. Data has been destroyed.\n"))


def display_file_contents() -> None:
    """Print the contents of the protected file to stdout (post-auth view)."""
    if not os.path.exists(PROTECTED_FILE):
        print(Color.red("[!] Protected file has already been deleted."))
        return

    print(f"\n{_divider()}")
    print(f"  PROTECTED FILE CONTENTS : {PROTECTED_FILE}")
    print(f"{_divider()}\n")

    with open(PROTECTED_FILE, "r", encoding="utf-8") as fh:
        print(fh.read())

    print(f"{_divider()}\n")


# ══════════════════════════════════════════════════════════════
#  INTERACTIVE ENTRY POINT  (manual testing)
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{_divider()}")
    print(Color.bold("  GUARDIAN PRO — SECURE LOGIN MODULE (Interactive Test)"))
    print(f"{_divider()}\n")

    initialize_system()

    print(f"\n{Color.cyan('[*]')} System ready.")
    print(f"{Color.cyan('[*]')} Correct password  : {Color.bold(CORRECT_PASSWORD)}")
    print(f"{Color.cyan('[*]')} Max attempts      : {MAX_ATTEMPTS}")
    print(f"{Color.cyan('[*]')} Rate-limit delay  : {DELAY_SECONDS}s per failure\n")

    while not system_locked:
        try:
            pwd = input("Enter password (or 'quit'): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Interrupted.")
            break

        if pwd.lower() == "quit":
            print("[*] Session terminated by user.")
            break

        if check_password(pwd):
            display_file_contents()
            break

    print(f"\n[*] Session ended.  Audit log → '{LOG_FILE}'\n")
