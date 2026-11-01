# KeeShare Android journey coverage

**Paused by explicit user decision; incomplete and not accepted.** No further emulator attempts are running. See the pause record in [the verification inventory](../../../docs/features/keeshare-verification.md).

Latest corrected stream received 233,408,000/278,924,175 required bytes with ADB exit 0; provenance correctly failed before all local cases. Prior final-APK `run-powpi9gh` independently verified full installed bytes and passed only bounded foreign-device IOC fallback. Its empty-path reference has no result status (unresolved product/requirement gap); descendant and writable-control checks failed on identified harness setup/expectation issues, since corrected but not runtime verified. Continuation and removal cases remain not-run. Earlier failed ledgers are unchanged. No product fix5, commit, or merge occurred.

**Full feature acceptance remains open.** The current [verification inventory](../../../docs/features/keeshare-verification.md) maps every original acceptance criterion and journey step, records all review/repair rounds and lists remaining requirements separately from additional review coverage. This file supplies execution commands and preserves historical phase evidence. `not-run`, `running` and `failed` are not passes.

All behavior sessions use a new disposable Android36 emulator and private ADB through `kp2a e2e`, synthetic data, qualified `adb -s` and the runner artifact directory. No existing emulator/device is a test target. This documentation task launched no session. Secure PNGs may be black; fresh XML/window observations and independent pulled-file checks supply evidence. Installed APK identity must pass the full-byte provenance gate; do not substitute a host-path hash.

## Current evidence

Final repair4 APK SHA256: `98149d7c99a16222d02208a009e27ceaad9d1b2a851a2f609db7671577255216`. Source review3 is clear; final build exit0 and parent118 tests passed. `run-ips13r52/keeshare/two-db-results.json` records all15 ordinary-route cases passed, exit0: search→group handoff, baseline, accept automatic Both, one-Cancel decline, one-Back dismissal and duplicate-UUID owner mutations. It does not establish controlled callback timing, lock/background/replacement or pending current-database switching. Prompt disappearance has runtime XML checks plus retained activity/window samples and final XML; per-sample XML is not retained.

Final core: `run-ht1poe05`: 12 recorded passes; running: none; failed: none; exit marker: 0. Source: `.dev/e2e/run-ht1poe05/keeshare/results.json`, `/tmp/keeshare-final-core.log` and eventual `.exit`. Core success is recorded; broader requirements remain open.

Earlier APK `4207369bb9d2349bd58befdfba55e5735f53fe7b6757d6f472950ca326f9179b` has strict original10 + engine-change/deletion + wrong-key passes in `run-mcumo38o`; these are earlier-build evidence. Corrected extended `run-4z4y2pev` records recursive export, nested config merge, three warm sync cycles and existing Downloads cancel passes, then preference-navigation failure. `run-nfn5xyja` separately records preference recovery and editor recreation/cancel passes before reload-navigation failure. Foreground `run-w7e7y8q2` exit0 proves accepted parent and explicit-sync export, not automatic Both. All paths are `.dev/e2e/<run>/keeshare/`.

Persisted safety `run-kk7uojrt`, `run-imxr55p8`, `run-5h74n3cn` each record nine passes on that earlier APK (newer-entry/newer-descendant/different-creation controls). Different-type `run-gxw9prqf` failed APK collection before initialization, exit1, no results JSON; no behavior pass. The initial recycle-message failure `run-uk9vdumf` remains failed. APK B `6354520724f2a0b456cc367eb746b3face3154fb1daac4c59526a4042287fd90` search-lock run-k72aak2b is a contention diagnostic, not repaired-route acceptance.

Only live SMB/Samba is explicitly waived. Cloud credentials/provider access and modern Android/nonexported-activity constraints justify unavailable routes but do not waive required behavior checks. Current required slices and deferred Minor findings are in the inventory, with exact source/runtime report paths.

## Repeatable commands

From repository root, build/test once when source changes:

```sh
nix run . -- -c 'kp2a build && kp2a test'
```

Core (original ten steps plus real remote add/change/delete and wrong-key atomicity):

```sh
nix run . -- -c 'kp2a e2e --apk /home/sinkerine/dev/keepass2android/src/keepass2android-app/bin/Debug/net9.0-android/keepass2android.keepass2android_debug-Signed.apk -- python3 -B tests/e2e/keeshare_journey.py'
```

Extended, separate fresh session with enriched synthetic fixtures:

```sh
nix run . -- -c 'kp2a e2e --apk /home/sinkerine/dev/keepass2android/src/keepass2android-app/bin/Debug/net9.0-android/keepass2android.keepass2android_debug-Signed.apk -- python3 -B tests/e2e/keeshare_journey.py --extended'
```

Resume remaining regression checks from synthetic **files only**, into a fresh emulator (replace path with the extended run's `keeshare/` directory):

```sh
nix run . -- -c 'kp2a e2e --apk /home/sinkerine/dev/keepass2android/src/keepass2android-app/bin/Debug/net9.0-android/keepass2android.keepass2android_debug-Signed.apk -- python3 -B tests/e2e/keeshare_journey.py --resume-regressions .dev/e2e/run-ak6n4h9o/keeshare'
```

Bounded preference/reload/recreation-only phase uses the same seed, removing only its inactive nested reference to keep three configured rows (original nested assertions retain their own evidence):

```sh
nix run . -- -c 'kp2a e2e --apk /home/sinkerine/dev/keepass2android/src/keepass2android-app/bin/Debug/net9.0-android/keepass2android.keepass2android_debug-Signed.apk -- python3 -B tests/e2e/keeshare_journey.py --resume-regressions .dev/e2e/run-ak6n4h9o/keeshare --remaining-only'
```

Additional dedicated slices (use a matching approved APK pin; historical pinned scripts may require deliberate provenance updates before execution):

```sh
nix develop --command kp2a e2e --apk /absolute/approved.apk -- python3 -B tests/e2e/keeshare_two_databases.py --advanced-search
nix develop --command kp2a e2e --apk /absolute/approved.apk -- python3 -B tests/e2e/keeshare_local_safety.py --collision different-type
```

## Historical writer checkpoint

The following text records the earlier T8 writer checkpoint on APK A. Its then-pending cases are superseded only by the explicitly named later evidence above and in the inventory. Assertions that a rerun or reviewer was still pending describe that checkpoint; they do not negate later records. No raw historical result is changed.

## Observed results

APK SHA256 `4207369bb9d2349bd58befdfba55e5735f53fe7b6757d6f472950ca326f9179b`.

| Case | Actual evidence | Limit |
|---|---|---|
| All original 10 steps | **Passed** together, `.dev/e2e/run-1c012x6i/keeshare/results.json`; run13 exit0 | Opening route adjustment below |
| Engine import add/change/delete | **Passed** in core13, pulled `engine-changed-main.kdbx` and `engine-deleted-main.kdbx` | Local move/recycle conflicts not tested |
| Corrupt file | **Passed** core13: real Downloads document picker, invalid-signature row, no crash and full decrypted DB equality after persisted IOC baseline | Other format failures untested |
| Wrong key | **Passed** core13: visible incorrect-password result, full decrypted DB unchanged | Fault-injected storage/read-only save untested |
| Secret/private-path log audit | **Passed** core13, raw `journey-logcat.txt` | Checks three fixture passwords and private-path KeeShare diagnostics |
| Recursive export sanitization/times | **Passed** extended15 `.dev/e2e/run-ak6n4h9o`: plain and zip, three group depths, unrelated metadata retained, timestamp/usage preserved, source descendant state unchanged | Nested valid references covered in sync fixture; plain fixture has malformed references plus sharing keys |
| Genuine nested merge/local config | Android content change and exact local sharing keys **passed** extended15; final verifier failed on equivalent ISO vs binary time encodings. Corrected decoded-time offline verification passed `.dev/keeshare-t8/run15-offline-verification.log` | Full corrected extended session still needs parent rerun; no deletion/new-remote-credential controls |
| Three repeated sync cycles | **Passed** fresh seeded run16 `.dev/e2e/run-sszg0i6g` | Warm cycles after one fresh open; full multiple reopen convergence matrix incomplete |
| Picker no pre-save mutation | **Passed** run16: real writable Downloads document select/editor cancel, sentinel bytes/size/mtime and database bytes unchanged | New paths, rejected grants/provider permutations unverified |
| Import disabled/reload/editor recreation | Bounded run17 `.dev/e2e/run-ofv5uiq8` displayed correct required-import skip, but automation failed reading a preceding clipped row's status. Innermost-row helper correction is syntax checked only | Skip atomicity/re-enable recovery, reload and recreation remain unverified; no further session authorized in writer slice |
| Longer list navigation | **Unresolved**: zero-row XML in run10/11 after partial-row positioning; repeated large-scroll screenshot investigation run-6blgs11a rendered rows. Run14/16 also failed locating rows. Root cause unknown; no source repair attributed | Do not call these passes or silently waive |

## Approved entry-route adjustment

Modern Android removes the built-in `file` browser from the storage screen. Supervisor approved opening **only** the main app-private fixture via normal exported `kp2a.action.SelectCurrentDbActivity` file-opening intent. Real password input is asserted in memory, remasked, Unlock tapped, and both group names asserted. No password extra is supplied. `/data/data/<package>/files` is used because `/data/user/0` went into obsolete external permission setup in this build. Evidence: run-1koplpq_ storage screen; run-xiwmyre5 and run-0b0s10ms permission cancellation. Device-file selection uses real Android Downloads provider, not preloaded IOC.

Final writer verification: syntax checks and `git diff --check` passed, index empty, no generated pycache remains, no runner/emulator from these sessions remains. `.dev/keeshare-t8/phase-summary.json` consolidates actual phase results without rewriting their original failed statuses. The corrected timestamp and innermost-row helpers require an independent parent rerun.

## Uncovered original acceptance versus added matrix

Original criteria still lack complete evidence for cross-device isolation/missing location (AC5), all descendant/move/edit read-only paths (AC6), per-share continuation/read-only database/save and I/O failures (AC7), removal/mount UI and complete states (AC9), nonlocal offline recovery (AC10), and final complete journey gate (AC11, subject to recorded final-core outcome). AC3/4 trigger/export variants also have bounded rather than exhaustive runtime coverage. The [original criteria table](../../../docs/features/keeshare-verification.md#original-acceptance-criteria) records each limit.

Additional required review controls include different-type/plain safety, nonempty tombstones/live-memory atomicity, cold convergence and nested deletion/new credentials, controlled reload timing/cancellation/switch/reopen failure, direct/stale/mixed mutation and history/TAN, password B/empty reentry/process death, destination/grant/provider permutations and ordinary Import picker/copy regression. These remain open unless an owner explicitly defers them; they are [listed separately](../../../docs/features/keeshare-verification.md#additional-review-matrix-still-open) from the original11/10. Deferred Minor UI/evidence issues and unresolved scrolling/ADB causes are documented there. No feature-completion claim follows from a bounded pass.
