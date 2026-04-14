#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          GUARDIAN PRO — DEMO RUNNER                          ║
║          Module : run_demo.py                                ║
╚══════════════════════════════════════════════════════════════╝

Orchestrates a complete end-to-end demonstration:
  1. Manual login test  → verifies correct / wrong credentials
  2. Brute-force attack → shows defence mechanism triggering

Run this to get a full walkthrough of all system capabilities
in a single command: python3 run_demo.py
"""

import os
import sys
import time


# ══════════════════════════════════════════════════════════════
#  TERMINAL HELPERS
# ══════════════════════════════════════════════════════════════

class C:
    _on = os.isatty(1)
    _w  = staticmethod(lambda c, t: f"\033[{c}m{t}\033[0m" if C._on else t)
    red    = staticmethod(lambda t: C._w("91", t))
    green  = staticmethod(lambda t: C._w("92", t))
    cyan   = staticmethod(lambda t: C._w("96", t))
    bold   = staticmethod(lambda t: C._w("1",  t))
    dim    = staticmethod(lambda t: C._w("2",  t))

DIV = "═" * 60


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header(text: str) -> None:
    print(f"\n{DIV}")
    print(C.bold(f"  {text}"))
    print(f"{DIV}\n")


def pause(msg: str = "Press Enter to continue…") -> None:
    try:
        input(C.dim(f"\n  ↵  {msg}\n"))
    except (EOFError, KeyboardInterrupt):
        print()


# ══════════════════════════════════════════════════════════════
#  DEMO PARTS
# ══════════════════════════════════════════════════════════════

def part1_manual_login() -> None:
    """
    Interactive login test.

    Demonstrates:
      • Correct-password flow  → vault unlocked, contents displayed
      • Wrong-password flow    → strike recorded, rate-limit applied
    """
    header("PART 1 — Manual Login Test")

    try:
        import login
    except ImportError:
        print(C.red("[!] login.py not found. Make sure it is in the same directory."))
        return

    login.initialize_system()

    print(f"  Correct password  : {C.bold(login.CORRECT_PASSWORD)}")
    print(f"  Max attempts      : {login.MAX_ATTEMPTS}")
    print(f"  Rate-limit delay  : {login.DELAY_SECONDS}s per failure\n")

    # Test an intentionally wrong password first
    print(C.dim("[demo] Trying WRONG password '000'…"))
    time.sleep(0.5)
    login.check_password("000")

    pause("Wrong-password demonstrated. Press Enter to test the CORRECT password…")

    # Reset state to avoid triggering lockout from the one bad attempt
    login.failed_attempts = 0
    login.system_locked   = False

    print(C.dim(f"[demo] Trying CORRECT password '{login.CORRECT_PASSWORD}'…"))
    time.sleep(0.5)
    if login.check_password(login.CORRECT_PASSWORD):
        login.display_file_contents()


def part2_brute_force() -> None:
    """
    Automated brute-force simulation.

    Re-initialises a fresh target system so the attack always has
    something to attack, regardless of the Part 1 outcome.
    """
    header("PART 2 — Brute Force Attack Simulation")
    print("  The attacker will now systematically try every 3-digit")
    print("  combination (000 → 999) against a freshly armed system.\n")
    print(C.dim("  Observe: the defender triggers self-destruct after just 3 failures.\n"))

    pause("Press Enter to launch the attack simulation…")

    try:
        import login
        import brute
    except ImportError:
        print(C.red("[!] login.py or brute.py not found."))
        return

    # Fresh start so we always have a valid protected file
    login.initialize_system()

    brute.brute_force_attack()
    brute.display_attack_statistics()


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main() -> None:
    clear()

    print(f"\n{'#' * 60}")
    print(C.bold(C.cyan("#  GUARDIAN PRO — FULL SYSTEM DEMONSTRATION")))
    print(f"#{'─' * 58}#")
    print("#  This demo covers:")
    print("#    1. Manual login (correct & wrong passwords)")
    print("#    2. Automated brute-force attack + defence")
    print(f"{'#' * 60}\n")

    pause("Press Enter to begin the demonstration…")

    part1_manual_login()

    pause("Part 1 complete. Press Enter to continue to Part 2…")

    part2_brute_force()

    header("DEMO COMPLETE")
    print(C.green("  Both scenarios successfully demonstrated."))
    print(f"\n  Artefacts generated:")
    print(f"    {C.cyan('access_log.txt')}  — full audit trail")
    print(f"    {C.cyan('protected.txt')}   — present (if Part 1 succeeded) or wiped")
    print(f"\n  {C.dim('Guardian Pro system standing by.')}\n")


if __name__ == "__main__":
    main()
