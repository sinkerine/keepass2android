# KeeShare Android journey coverage

## User disposition

The user explicitly accepted delivery with documented residual coverage, deferring the six additional review groups recorded in the verification inventory. Those groups were not run and are not passes. Original acceptance gates and the final focused checks are accepted. No new commit or merge is authorized by this decision. Historical open/failed/not-run descriptions below remain evidence checkpoints, superseded only in acceptance status by this disposition.

## Final focused gates accepted

The final review accepted move-IN refusal (`run-tjc6g7gx`), Export-only edit/readable export and populated KeepGroups=False exclusion (`run-69jh8qo4`), and empty-path UI-picked current-device IOC import (`run-r357f4eo`, exit0), all on repair5 APK G. Parent independently checked full installed hashes and persisted outputs. Earlier failed ledgers below are historical and unchanged; their missing-case descriptions are superseded by these later scoped passes. See the final reconciliation in [the verification inventory](../../../docs/features/keeshare-verification.md). Original gates are supported; full acceptance awaits explicit user disposition of the remaining additional review matrix.

**Current: resumed after infrastructure mitigation; repair5 authorized and independently source-reviewed with no issues. Full feature acceptance and merge approval remain open.** The [verification inventory](../../../docs/features/keeshare-verification.md) maps original11 criteria and original10 steps to exact build/run boundaries and separates remaining original evidence from the still-required review-added matrix. No additional staging, commits or merge is authorized. This documentation task launched no session.

All behavior sessions use a new disposable Android36 emulator and private ADB through `kp2a e2e`, synthetic data, qualified `adb -s` and the runner artifact directory. No existing emulator/device is a test target. This documentation task launched no session. Secure PNGs may be black; fresh XML/window observations and independent pulled-file checks supply evidence. Installed APK identity must pass the full-byte provenance gate; do not substitute a host-path hash.

## Current evidence

Final **G / repair5** APK SHA256: `b50e06bf1e48eb7dd8657610d84f1ceaa89fd31058e3c6fa1680d743b730b8f2`, 278,924,175 bytes. Build exit0 (0 errors, 5,112 warnings), parent product tests **124 (8+116)** and final Python tests **54 passed**. Repair5 changes only two direction predicates, comment and six host cases relative to predecessor F's product source; it leaves codec/IsValid intact.

| Final-G run | Actual evidence | Limit |
|---|---|---|
| `run-obajlvsi` | Original10 + engine add/change/delete + wrong-key atomicity passed; log audit passed; `/tmp/keeshare-r5-core-corrected.exit` 0 | Extended entries in core ledger remain not-run; no rewrite from separate suites |
| `run-x_es8qeu` | Seven original bounded cases passed: foreign-device IOC fallback, missing/unresolvable location, nested read-only, ordinary/Sync edits, failure continuation, reference/all-IOC removal; inactive control passed | Overall exit1 remains: extra empty-path/current-device IOC picker case failed before Save; Android combination unverified, P2 / Minor harness finding, no product defect established |
| `run-qkg4lay7` | All4 passed, exit0: offline nonlocal skip/no synthetic-endpoint requests with local positive control; automatic online recovery; real mount picker/derive/create/unpicked peer/remove and persisted state | Synthetic WebDAV, not SMB/authentication or all provider/mapping variants |

The parent independently hashed retained installed APKs and decrypted outputs from both local and offline/mount runs; guest hash, full size and stable package paths agree with G. Exact [local review](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/87ec5bf1-3bd9-40e2-8bd2-432b35a8b3a7/keeshare/E2E-repair5-local-review.md) and [offline/mount review](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/60fd1fac-b323-48bf-b0e4-bab48cce5436/keeshare/E2E-offline-mount-review.md) bound the claims. The local review's core-pending checkpoint is superseded by the completed core above, without changing that report.

**Predecessor F / repair4**, SHA256 `98149d7c99a16222d02208a009e27ceaad9d1b2a851a2f609db7671577255216`: source review3 clear; build and118 product tests passed. `run-ips13r52` all15 ordinary route cases passed, exit0: search→group handoff, baseline, accept automatic Both, single Cancel/Back, duplicate-UUID owner mutations. This remains **F runtime**, not G. Controlled callback timing/lock/background/replacement/pending switching remains open. Fresh XML was checked but only activity/window samples and final XML retained. F core `run-ht1poe05` also passed all12, exit0; G core now provides separate final-build proof.

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

Concrete original evidence still requiring final review disposition: **AC3** background/pending sync and full outside-group preservation beyond bounded comparisons; **AC4** explicit KeepGroups=False subgroup exclusion runtime; **AC6** move-in/out refusal and Export-group editability; **AC7** failed-import save/I/O safety and complete preservation beyond checked state. These are incomplete evidence, not known product failures. AC11's named build/host/journey gate now passes on G. AC5/9/10 bounded local/device/missing-location/removal/mount/offline slices now have the recorded G evidence; live SMB alone remains waived. Source/host evidence may suffice for some unexecuted variants, but that requires explicit final review disposition, not a silent downgrade. The extra empty-path/current-device IOC repair regression remains unverified after picker failure.

Additional required review controls remain separate: different-type/plain safety, nonempty tombstones/live-memory atomicity, cold convergence and nested deletion/new credentials, controlled reload timing/cancellation/switch/reopen failure, direct/stale/mixed mutation and history/TAN, password B/empty reentry/process death, destination/grant/provider permutations and ordinary Import picker/copy regression. No new waiver is inferred. Deferred Minor findings include rejection-dialog rotation/blank picker, SMB CloseFile masking, pre-recorder missing failure evidence, missing durable per-sample F XML, unexplained long-list XML/scrolling, and the new P2 picker harness failure. The settled-runner/verified-transfer mitigation remains separate from the unknown internal ADB/emulator root cause; see the [infrastructure report](../../../docs/e2e-adb-transfer-reliability.md).

The next step is consolidated final review and explicit disposition of these named gaps and required review controls. No feature completion or merge approval is granted by this inventory. Historical failed ledgers and earlier-build boundaries remain intact.
