# Isolated emulator ADB transfer reliability

Infrastructure investigation, 2026-10-31. This work did not touch the KeeShare feature, and it remains paused. Raw evidence is under `.dev/adb-transfer-infra/` (per-session launch, stdout/stderr, exit, private ADB server trace) and `.dev/e2e/run-*/adb-transfer-stress/attempts.jsonl` (per-attempt exit code, byte count, SHA-256, duration, device state). `.dev/adb-transfer-infra/aggregate.json` lists every session. Earlier failure artifacts were not modified.

## Finding

The private emulator's ADB link drops while the **guest is saturated**. In practice this means the burst of app starts for about 20 seconds after `sys.boot_completed`, during which guest CPU idle stays at 0–11%. The runner used to install the APK and start the child inside this window.

- The guest drops first. adbd logs `host-N: connection terminated: write failed`, and the ADB server then reads EOF (`read failed: Success`). The server reconnects within about 0.3–0.7 s, but **the link keeps dropping until the burst ends**. In one session it dropped five times in 16 s, so prompt retries also fail.
- `adb pull` reports these drops with exit 1. **`adb exec-out cat` exits 0 with truncated output**: exec-out uses the raw stream, so a closed transport looks like EOF. This explains the earlier 233408000-byte stream that exited 0. It is the same failure, not a separate bug.
- The following causes are ruled out: the KeeShare code, the APK contents (a random blob fails the same way), compression (`-Z` succeeds or fails only according to timing), private server or client versions, a foreign ADB server connecting to the emulator (guest connection IDs match the private server's own reconnects), host OOM, and guest memory pressure alone. Filling tmpfs caused 27 lmkd kills and 0 drops. Reinstalling the same package late in a session also caused no drops.
- Load contributes causally but is not fully characterized. Synthetic CPU saturation 60 s after boot caused 1 drop in 18 transfers (0 in 18 idle transfers in the same sessions), which is weaker than the real post-boot burst. The exact mechanism inside the emulator or the goldfish adb pipe is **unknown**, and no emulator-side fix is claimed. `-debug adb` could not be enabled without changing the runner. In one session the emulator also crashed at the moment of the drop (Crashpad output in `run-qoeg3lze/emulator.log`, emulator dead at teardown). The runner still reported success in that session, which is fixed below.

Confidence: **high** that the post-boot saturation window is the trigger for every observed failure without synthetic load. The private server traces recorded 20 drops. The 19 without synthetic load, including historical `run-pqgtohng`, occurred 35.9–53.9 s after transport registration, which is during the post-boot burst. In `cpu-1` that burst was saturated from 36 s to 45.4 s, and its length varies from session to session. There were no drops after the burst in about 300 later unloaded transfers. The 20th drop came at 101 s under synthetic CPU burn. Confidence is **low** about the internal mechanism.

## Results (fresh disposable AVD and private ADB server for every session; installed APK 278924175 bytes, SHA-256 98149d7c…5216)

| Condition | Sessions (with drops) | Transfers OK | Silent exit-0 truncations |
|---|---|---|---|
| Cold first reads at handover, ungated (old runner behavior) | 11 (4) | 43/51 | 6 |
| Same, 30 s delay | 6 (0) | 36/36 | 0 |
| Same, **settle gate (new runner)** | 8 (0) | 48/48 | 0 |
| Late in session: blob and APK × pull/exec-out/pull -Z | 1 (0) | 96/96 | 0 |
| Same-package reinstall then immediate transfer | 1 (0) | 64/64 | 0 |
| CPU burn 2 loops per vCPU at +60 s | 3 (1) | 35/36 | 1 |
| Guest memory pressure at +60 s | 3 (0) | 36/36 | 0 |
| Ungated, `pull_verified` without idle wait, mixed with exec-out | 8 (4) | `pull_verified`: 31/32 (1 failed closed after 3 retries) | 4 (exec-out) |
| Ungated, **`pull_verified` with idle wait**, mixed with exec-out | 8 (4) | `pull_verified`: **32/32**, 1 live drop recovered | 3 (exec-out) |

Also run with the new runner: the default `kp2a e2e` smoke check passed (`run-qj957alo`). A child that killed only its own emulator (`kill -9`) made the runner exit 1 with `Emulator exited with status -9 before teardown` (`run-z10_2007`). Before this change that run would have exited 0.

## Changes (infrastructure only, not committed)

- `tests/e2e/run.py`:
  - After boot and again after install, the runner waits until guest CPU idle is at least 50% for 3 consecutive one-second samples, then hands over. The samples are recorded in `settle.txt`. `--settle-timeout` (default 180 s, 0 skips) bounds the wait, and a timeout fails the run. The measured cost is 23–32 s after boot plus 4–11 s after install.
  - The runner now fails a run whose emulator exited before teardown.
- `tests/e2e/adb_transfer.py`, new. It contains:
  - `wait_until_idle`, which the runner gate also uses.
  - `pull_verified`, which:
    - accepts bytes only when the size and SHA-256 match what the guest reports independently before and after the transfer, plus an optional caller check such as stable `pm path` output, plus an optional expected hash;
    - deletes partial output and never resumes or concatenates;
    - retries only transport failures (nonzero exit, short output, timeout), at most 3 attempts, and only after the device reconnects **and** the guest is idle again;
    - refuses a full-size hash mismatch or a changed source or path immediately;
    - writes a JSON provenance record of every attempt.
- `tests/e2e/test_adb_transfer.py`, new. 13 host tests cover: clean transfer; exit-0 truncation retried and never accepted; disconnect/reconnect; bounded retries with partial removal; full-size wrong hash refused without retry; expected-hash mismatch; changed path; guest file changed; device never returns; guest stays busy; stale local file removed; idle-sample parsing and offline handling. Run them with `cd tests/e2e && python3 -B -m unittest test_adb_transfer`.
- `tests/e2e/adb_transfer_stress.py`, new. This is the standalone reproduction, independent of KeeShare: `kp2a e2e --settle-timeout 0 -- python3 tests/e2e/adb_transfer_stress.py --phases cold --methods exec-out,pull,exec-out` reproduces the failure in about 40% of fresh sessions.
- `docs/development.md`: one paragraph on the gate, crash detection and verified transfers.

## Limits

- This is a **mitigation that removes the trigger window plus integrity-preserving recovery, not a root-cause fix** in the emulator or adbd. A drop can still happen whenever a test itself saturates the guest. The gate guarantees nothing after handover. Large transfers should use `pull_verified`, and exec-out exit status must never count as completeness.
- The 50%/3-sample threshold comes from about 20 sessions on this host (KVM, emulator 36.3.10, platform-tools 36.0.0, Android 36 google_apis x86_64, 2 GB guest). A slower host could need a longer `--settle-timeout`.
- Session counts are modest: 0 of 14 gated or delayed sessions dropped, versus 8 of 19 ungated early sessions (one-sided Fisher p ≈ 0.005). The per-transfer separation is clearer.
- The KeeShare harnesses (`keeshare_journey.py`, `keeshare_two_databases.py`, `keeshare_local_acceptance.py`) still collect installed-APK provenance with their own pull/exec-out code. Switching them to `pull_verified` (with `check` = stable `pm path` and `expected_sha256` = the approved hash) is a small follow-up, deliberately not done while the feature is paused. The new runner gate already protects their startup provenance, because handover now happens after the burst.
- Crashpad writes to a shared `/tmp/android-$USER/emu-crash-*.db` outside the private directory. No dump was retained for the one crash. Cleanup was unaffected.
