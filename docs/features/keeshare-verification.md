# KeeShare verification inventory

## Paused by user decision

The user chose **Pause and preserve the incomplete result** after repeated installed-APK transfer failures. No further emulator attempts, source repairs, staging, commits or merge are authorized by this pause. The implementation and all raw evidence remain in the existing local checkout. **This feature is incomplete and not accepted.**

The latest run's correctly formed streamed read returned 233,408,000 of the required 278,924,175 bytes despite ADB exit 0 and empty stderr. The exact-size gate rejected it before fixture preparation. This adds no behavioral coverage; see the latest report at `/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/8c252d92-a9d3-4301-a745-9dc08a232521/keeshare/E2E-streamed-local-acceptance.4a4cae0c.d7809f53.md`. Both ordinary pull and alternate streaming remain intermittently unreliable; their root cause is unknown.

A prior correctly streamed, independently hashed final-APK run, `.dev/e2e/run-powpi9gh`, passed bounded foreign-device IOC isolation/relative fallback. It also exposed a genuine requirement gap: an active reference with an empty path has a visible not-set location but no skipped-result status, because reference predicates suppress processing before location resolution. This is unresolved; no fifth product repair was authorized. Imported-descendant checks were blocked by notification onboarding, and the writable-control test incorrectly required a group-only selection Edit action. Those harness corrections are implemented but unverified; the following run failed provenance before exercising them. Per-share failure continuation, full descendant/control checks and UI removal still have no new passes.

Final-build core (`run-ht1poe05`, exit 0, all ten journey steps plus add/change/delete and wrong-key checks) and reviewed ordinary reload/ownership (`run-ips13r52`, exit 0, all 15 cases) remain valid. They do not close the above requirements or the additional timing/provider/offline gaps listed below. Live SMB/Samba remains the only explicit testing waiver.

At pause, no owned runner/emulator was observed, whitespace checks passed and the index was empty. Resume requires an explicit new instruction; restore reliable full installed-byte verification before additional Android assertions, preserve failed result ledgers, and address or explicitly decide the empty-path requirement rather than marking it passed.

Snapshot: 2026-11-01T03:53:02+00:00. **Full feature acceptance remains open.** The approved implementation and source gates, the final ordinary runtime route, and earlier bounded runtime evidence are recorded below. A pass applies only to its named APK and executed cases. Raw `failed`, `running` and `not-run` results remain authoritative.

The [approved plan](keeshare-plan.md) defines 11 original acceptance criteria and ten journey steps. [Android coverage](../../tests/e2e/keeshare/coverage.md) gives repeatable slices. Artifact paths beginning `.dev/` are relative to `/home/sinkerine/dev/keepass2android`; external review links are exact session artifacts.

## Decisions and scope

- The user approved work directly in the local main worktree, with no commits or staging. Base remains the user's environment commit `42e395f99b286b32b919bfd2f6a80c27e860a36a`; preserve its setup, skill, development guide, SDK tooling, runner, ignore rules and Dropbox project line. Additive feature edits to `flake.nix`, `scripts/kp2a` and the business project do not replace that setup.
- PRs #3130 and #3106 were independent design references only. The approved wire format derives from KeePassXC. No source copying is asserted.
- Import, Export and Synchronize, both containers, per-device encrypted IOC/mount data and default-on preferences are approved. SMB support is required; **live SMB/Samba execution alone is explicitly waived**. Build, source status-check review and host path/credential tests remain required.
- Modern Android does not expose the old built-in file browser. Opening only the app-private main fixture through exported `kp2a.action.SelectCurrentDbActivity`, with actual password UI and no password extra, was approved. Device-file choices use the real Downloads document provider. Nonexported Entry/EntryEdit activities were not exposed for testing; a supported in-app seam is needed for direct/stale-intent checks.
- Missing cloud credentials/provider access justifies unavailable execution, not a pass or waiver. Ordinary local checks still need execution. The user authorized repair4 coalescing; its final review3 has no remaining source finding. No repair5 is proposed.

## Build identities and runtime ledger

| Identity | Exact APK SHA256 | Evidence boundary |
|---|---|---|
| A, repair1 | `4207369bb9d2349bd58befdfba55e5735f53fe7b6757d6f472950ca326f9179b` | Earlier core/extended, persisted safety, foreground and preference/recreation evidence only |
| B, repair2 UTC | `6354520724f2a0b456cc367eb746b3face3154fb1daac4c59526a4042287fd90` | Search-lock diagnostic and owner-deletion follow-up context; not final coalescing proof |
| C, repair3 search | `7bc377f6597afdb3851ea18b563a515e47012a2422addd9ff39fa5440342494b` | Search handoff repair; subsequent duplicate-prompt failure retained |
| D, initial repair4 | `aa7c5e2595ce3afb92c20566f3a6a1216e3b7236701fd47678b4bf4f22c571a2` | Intermediate source/build artifact, superseded after review fixes |
| F, final repair4 | `98149d7c99a16222d02208a009e27ceaad9d1b2a851a2f609db7671577255216` | Final source review3/build and parent 118 tests; ordinary runtime `run-ips13r52`; final core checkpoint below |

Final signed APK path: `src/keepass2android-app/bin/Debug/net9.0-android/keepass2android.keepass2android_debug-Signed.apk`. F is 278,924,175 bytes. `.dev/reload-repair4-fix-r2/final-validation.json` records final source/APK hashes, build exit0, 0 errors and 5093 warnings. Parent `/tmp/keeshare-parent-r4-fix2-tests.log` records 8 Autofill + 110 KeeShare passes, no failures/skips. The parent also reported 35 harness tests; the dedicated final runtime worker separately recorded seven provenance/recovery host passes. These gates do not execute Android lifecycle edges.

| Run / identity | Raw outcome and supported evidence | Limit |
|---|---|---|
| `run-ips13r52` / F | `two-db-results.json`: all15 `passed`, runner exit0, 913.05s. Full installed pull plus guest SHA equal F. Ordinary Advanced Search → visible Sync → real resumed group; unchanged baseline; accept/Cancel/Back; duplicate UUID owner edit/cancel/recycle/permanent delete | Controlled lifecycle/timing matrix unrun |
| `run-ht1poe05` / F | `run-ht1poe05`: 12 recorded passes; running: none; failed: none; exit marker: 0. `.dev/e2e/run-ht1poe05/keeshare/results.json`, `/tmp/keeshare-final-core.log`, `/tmp/keeshare-final-core.exit` when created | Core finished; broader required gaps remain. |
| `run-mcumo38o` / A | Strict core: all original10 plus `engine-add-change-delete` and `wrong-key-atomic` passed; parent exit0. Installed-base identity in `results.json` | Earlier APK; does not certify F |
| `run-1c012x6i` / A | Original10 together passed, exit0; remote changes/deletions, corrupt file and wrong-key atomicity | Historical harness recorded host APK identity; later strict installed-identity core provides stronger provenance |
| `run-4z4y2pev` / A | `recursive-export-metadata`, `nested-local-config-merge`, `repeat-sync-stability`, `picker-no-presave-write` passed; `import-disabled-safe-skip` failed (`Missing scrollable UI: Team Sync`) | Entire extended phase failed; three warm cycles, not full cold convergence |
| `run-ak6n4h9o` / A | Recursive export passed; nested merge failed timestamp representation verifier; corrected decoded-time offline verification passed `.dev/keeshare-t8/run15-offline-verification.log` | Original failed status retained; later nested pass belongs to run-4z4y2pev |
| `run-sszg0i6g` / A | Repeat cycles and existing Downloads select/cancel passed | New paths/grants/provider controls unrun |
| `run-kk7uojrt`, `run-imxr55p8`, `run-5h74n3cn` / A | Each nine local safety cases passed: older/equal placement preservation, actual UI move/recycle, cold reopen and respectively newer-entry/newer-descendant/different-creation collision refusal. Last two exit0; first has final bounded PASS but no separate exit marker | Persisted checks; baseline tombstones empty; no unsaved-memory atomicity proof; zip Synchronize only |
| `run-uk9vdumf` / A | Failed recycle-dialog wording assertion, later cases not-run; corrected script rerun separately | Historical harness failure retained |
| `run-gxw9prqf` / unknown installed identity | Startup installed-APK pull failed, exit1, no behavior cases or results JSON | Different-object-type collision remains unverified; underlying transport cause unknown |
| `run-nfn5xyja` / A | `editor-recreation` and `import-disabled-safe-skip` passed; later reload navigation failed. `run-hasjjve7`, `run-pvzcosnz` also retain preference recovery passes | Reentry cancel only; no B/empty-key save or process death |
| `run-w7e7y8q2` / A | Foreground reload exit0; no export overwrite before decisions/after decline/dismiss; accepted parent UUID/title, explicit Sync export and log audit passed | Five-second post-accept sample unchanged, expected foreground Import behavior; not automatic SyncUtil Both proof |
| `run-k72aak2b` / B | Diagnostic: search stayed Importing over12.34s; normal Back destroyed search, importer entered31ms later; root idle afterward | Confirms contention boundary, not passing repaired Sync; unchanged export proves preservation only |

F ordinary route: each live prompt had exactly one base plus one dialog window on the exact resumed GroupActivity. Captured SearchResults ActivityRecord stayed unchanged during external parent replacement. Pending exports matched baseline; accept reopened exact parent/entry UUID and automatically exported the changed title without explicit share-sync. One Cancel/Back removed the prompt, with five fresh runtime XML assertions and retained activity/window samples over12.17/12.16s; post-decision exports stayed byte-identical. Owner B mutations persisted while A stayed byte-identical. Internal Database object identity was not directly instrumented. Prompt timings include harness work and do not cover fast decisions. Finite logcat overwrote earliest initial/accept lifecycle lines; retained UI/window/hash artifacts remain. Secure-window PNGs may be black, so XML/window evidence carries those checks.

Primary F artifacts: `.dev/e2e/run-ips13r52/keeshare/{two-db-results.json,two-db-installed-provenance.json,two-db-commands.json,two-db-logcat.txt,installed-base.apk}`, per-decision `*-single-prompt.{activities,windows}.txt`, prompt/final XML, `*-no-resurrection-*` dumps, accepted-parent and automatic-export files, and owner captures. Independent persisted verification and cleanup: `.dev/two-db-repair4-runtime/{persisted-verification.json,persisted-verification.log,verify.py,launch-status.json,cleanup.json,host-tests.log}`. See [E2E-repair4-runtime.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/91e389ef-8939-4f0d-9d55-87b0c2c81849/keeshare/E2E-repair4-runtime.md); [E2E-repair4-runtime-review.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/696c90e5-566f-43d5-bde3-0f5889b588ce/keeshare/E2E-repair4-runtime-review.md).

## Original acceptance criteria

“Partial” means evidence supports named portions but does not close the whole criterion. Earlier runtime is identified as A; final runtime as F. Source/build acceptance is distinct from runtime acceptance.

| AC | Evidence | Remaining original requirement / disposition |
|---|---|---|
| 1 Format | 110 KeeShare host tests and T1 review2: golden references, missing KeepGroups, base64, UUID order, encode/decode | Host/source gate passed; no separate live KeePassXC GUI roundtrip claimed |
| 2 Containers | Host magic/read/write tests; A strict core zip import/export and plain created export; F recorded core step5/6 passes | Verified portions on F; full core completion checkpoint above |
| 3 Import | A strict core add/change/delete, relative open import; F ordinary unchanged Sync and accept→Both; T4 scratch merge review3 | Background/pending sync and full trigger/lifecycle combinations unverified; outside-group protection bounded by safety limits |
| 4 Export | A strict core save and pykeepass verification; A recursive both-format metadata/time checks; F automatic Both changed export | Final full export matrix and KeepGroups variants beyond recorded cases unverified; cold convergence is additional review coverage |
| 5 Device location | Host precedence/device-key/relative tests; A corrupt picked IOC and relative paths; F core step3 passed | Actual A-device/B-device isolation and no-location UI branch not demonstrated; mount UI runtime incomplete |
| 6 Read-only | A and F core step4 absence of add/Delete/Move; T6/T7 ownership and Copy source fixes | Full subgroup/add/edit/delete/move-in/out UI matrix, stale/direct callbacks unverified |
| 7 Nonblocking/safe | Reviewed OperationRunner/locker paths; A wrong-key/corrupt persisted equality; local collisions A; F search reader release and stable idle | Per-share failure continuation, failed-save/read-only-main/faulted I/O and unsaved-memory atomicity remain unverified |
| 8 Secrets | A core log audit and recursive export sanitization; F runtime raw/scenario logcats contain no three synthetic passwords; source audit/review | Fixture audit is bounded; does not establish all provider errors/credentials |
| 9 Config UI | A original step7/8/9; F recorded steps7/8; T6 create/edit/remove/picker source gate | Removal, mount creation/removal and full last-result/location states not fully exercised |
| 10 SMB | Host UNC/credential/mount tests, T9 checked NTStatus/build/review2; resolver/offline source review | Live SMB explicitly waived. Nonlocal offline→online runtime and mount/UNC UI evidence remain unverified; generic provider unavailability is not waived |
| 11 Tests/build/journey | F build and118 tests passed; F15-case ordinary route passed; A strict original journey passed | F core completed; required gaps above prevent full delivery acceptance |

## Original ten-step journey

| Step | Earlier A | Final F at snapshot |
|---|---|---|
| 1. Prepare | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 2. Password open / groups | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 3. Relative automatic import | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 4. Read-only visible controls | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 5. Zip Synchronize import | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 6. Save and verify zip export | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 7. Configuration rows | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 8. Create Personal export / strip reference | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 9. Picked corrupt file / failed row / unchanged DB | `passed` run-mcumo38o | `passed` run-ht1poe05 |
| 10. Secret/private-path log audit | `passed` run-mcumo38o | `passed` run-ht1poe05 |

Step2 uses the approved exported open-file route because the original internal browser is absent on Android36. No earlier failure is rewritten by a later pass. Final ordinary two-database secret checks supplement but do not replace original step10's private-path audit.

## Additional review matrix still open

These requirements arose during review and remain separate from the original11/10 mapping. They are required unless the owner explicitly changes acceptance. Only live SMB execution is waived.

- **Safety/import:** different-object-type collision; nonempty existing tombstones; forced save/live-memory collision atomicity; automated comparison of all unrelated outside objects/parents; plain-format safety variants. Existing older/equal/newer descendant and creation-provenance controls have earlier A evidence.
- **Export/nesting:** repeated cold-reopen convergence, Remove sharing timestamp behavior, matching nested deletion staying deleted and stripping newly arriving remote credentials, both formats after those controls. Recursive sanitization, source immutability and local nested config preservation have bounded A passes.
- **Lifecycle/ownership:** controlled finishing-QuickUnlock/pre-OnResume result delivery; lock/background/close/replacement cancellation; late callbacks and GUID stale tokens; current DB switching/two pending targets; rapid taps/fast decisions; rotation/timeout; canceled/failed reopen and unrelated later open; cached instance replacement; AutoOpen completion/cancel, pending sync drain/dedup and selector recreation; reader-acquisition failure. F ordinary route clears its reproduced failure only.
- **Read-only/mutation:** import descendants/direct stale entry/editor callbacks, mixed/combined/search selections, move/paste/copy guards and editable regular/Export/Sync controls, real lock/detached refusal, history/TAN. Nonexported entry activities justify no external-intent launch; they do not waive supported in-app refusal checks.
- **Editor/destination:** password reentry save with B/empty password, repeated recreation/process death, draft IOC/mount retention and saved-state secrecy; rejected read-only/backup/missing-parent local paths; new local destination only after Save; temporary/read-only document grants; no pre-save append/truncate/create/copy/upload across repicking, clearing and mount choices. Existing writable Downloads cancel and recreation cancel have A passes.
- **Offline/providers:** nonlocal offline skip and online recovery; cache/cloud behavior; OneDrive variants and Google Drive full/app-data new-name rejection/existing-file acceptance with provider operation evidence; ordinary Import picker/copy regression. Credentials/provider access were unavailable. Owner must supply access, accept an explicit deferral, or keep these blocked.

## Review and repair gates

Task source review rounds: T1/T2/T3/T9 each two; T4 three; T5/T6/T7 each two; T8 harness three. Final task source/build gates found no remaining Critical/Important issue; T8's bounded harness gate does not accept missing runtime coverage. Important findings were fixed under parent rulings; T4's recursive credential export finding was Critical and fixed by recursive clone sanitization. T4 subsequent rounds fixed touched clone timestamps, nested local sharing preservation and newer-child placement rejection. T5 fixed stale export before reload; T6 fixed password recreation, owner identity, Copy protection and pre-save/provider selection; T7 fixed lifecycle owner initialization and wrong-clone deletion. T8 fixed installed provenance and stale/empty UI capture negative assertions.

Repair1 initialized the temporary remote database before parsing corrupt headers and removed private destination diagnostics. Repair2 corrected deletion timestamps to UTC after a real serializer assertion, preserving owner routing. Repair3 closes search and releases its lifetime reader before one-shot Sync on a usable resumed host; the API seam and intentional search closure were parent-approved. Its subsequent runtime exposed duplicate reload dialogs. User-authorized repair4 coalesces exact-target requests, strongest Both intent and GUID routing; review1 fixed ordinary-navigation invalidation and UI thread ownership, review2 required retaining changed results across finishing/pre-resume handoff, review3 cleared source. The later F ordinary route and independent runtime review passed within their stated boundaries.

Deferred Minor findings and limits:

- Export rejection dialog rotation can leave a blank picker; system Back recovers. T6 review2 explicitly deferred this.
- SMB CloseFile failure can mask an earlier I/O error; T9 notes remain report-only, live failure handling not executed.
- Local safety startup before recorder initialization produced no JSON or useful pull stderr for run-gxw9prqf; deferred Minor, behavior unverified.
- F ordinary postdecision samples assert fresh XML at runtime but do **not** retain each XML: only activity/window samples and final XML remain. Do not call these durable per-sample XML artifacts.
- Long-list zero-row XML versus harness scrolling remains unexplained (run10/11/14/16-era failures; run-6blgs11a rendered rows during investigation). No product defect or source repair attribution established.
- Intermittent ADB transfer failure root cause remains unresolved. Full-byte provenance gates and one bounded private reconnect recovery remain; F ordinary full pull succeeded without recovery.

## Minimal remaining action

Read the final core exit/results once recorded; do not rerun an active parent session or infer its outcome. Then close original AC5/6/7/9/10 gaps through bounded device-isolation/missing-location, read-only descendant/mutation, failure-continuation/read-only-main, mount/removal and offline recovery slices. Recheck affected earlier A behaviors on F as needed for final-build claims. For the added matrix, prioritize different-type safety, fast/late reload cancellation plus pending switch/reopen failure, password reentry save, and local destination/grant safety. Provider credentials and nonexported in-app test seams require owner support or an explicit acceptance deferral. No broader refactor or new product repair is justified by the current ordinary-route pass.

## Final working-tree inventory

The inventory is against the preserved environment HEAD, including untracked files; a tracked-only `git diff --stat` is incomplete. No commit or staging is requested. Generated runtime evidence lives under ignored `.dev/`, while review reports live outside the repository.

Tracked changes (M modified, D deleted; exception relocation retains namespace):

```text
M	flake.nix
M	scripts/kp2a
M	src/KeePass.sln
M	src/Kp2aBusinessLogic/Io/SmbFileStorage.cs
M	src/Kp2aBusinessLogic/Kp2aBusinessLogic.csproj
M	src/Kp2aBusinessLogic/OperationRunner.cs
M	src/Kp2aBusinessLogic/PreferenceKey.cs
M	src/Kp2aBusinessLogic/SelectStorageLocationActivityBase.cs
M	src/Kp2aBusinessLogic/UiStringKey.cs
M	src/Kp2aBusinessLogic/database/CheckDatabaseForChanges.cs
M	src/Kp2aBusinessLogic/database/edit/DeleteRunnable.cs
M	src/Kp2aBusinessLogic/database/edit/SaveDB.cs
M	src/keepass2android-app/EntryActivity.cs
M	src/keepass2android-app/EntryEditActivity.cs
M	src/keepass2android-app/GroupActivity.cs
M	src/keepass2android-app/GroupBaseActivity.cs
M	src/keepass2android-app/Resources/layout/group.xml
M	src/keepass2android-app/Resources/menu/group_entriesselected.xml
M	src/keepass2android-app/Resources/values/strings.xml
M	src/keepass2android-app/Resources/xml/pref_app_file_handling.xml
M	src/keepass2android-app/Resources/xml/pref_database.xml
M	src/keepass2android-app/SelectCurrentDbActivity.cs
M	src/keepass2android-app/SelectStorageLocationActivity.cs
M	src/keepass2android-app/SyncUtil.cs
M	src/keepass2android-app/app/App.cs
D	src/keepass2android-app/app/NoFileStorageFoundException.cs
M	src/keepass2android-app/search/SearchResults.cs
```

Untracked feature, host tests, Android resources and E2E/docs (all must be included in delivery review):

```text
docs/features/keeshare-plan.md
src/Kp2aBusinessLogic/Io/NoFileStorageFoundException.cs
src/Kp2aBusinessLogic/KeeShare/KeeShareExporter.cs
src/Kp2aBusinessLogic/KeeShare/KeeShareGroups.cs
src/Kp2aBusinessLogic/KeeShare/KeeShareImporter.cs
src/Kp2aBusinessLogic/KeeShare/KeeShareLocationResolver.cs
src/Kp2aBusinessLogic/KeeShare/KeeShareScheduler.cs
src/Kp2aBusinessLogic/KeeShare/KeeShareSyncOperation.cs
src/Kp2aKeeShare.Tests/KeeShareContainerTests.cs
src/Kp2aKeeShare.Tests/KeeShareMountMapTests.cs
src/Kp2aKeeShare.Tests/KeeSharePathTests.cs
src/Kp2aKeeShare.Tests/KeeShareReferenceTests.cs
src/Kp2aKeeShare.Tests/KeeShareSmbPathTests.cs
src/Kp2aKeeShare.Tests/KeeShareTreeFingerprintTests.cs
src/Kp2aKeeShare.Tests/Kp2aKeeShare.Tests.csproj
src/Kp2aKeeShare/KeeShareContainer.cs
src/Kp2aKeeShare/KeeShareMountMap.cs
src/Kp2aKeeShare/KeeSharePath.cs
src/Kp2aKeeShare/KeeShareReference.cs
src/Kp2aKeeShare/KeeShareSmbPath.cs
src/Kp2aKeeShare/KeeShareTreeFingerprint.cs
src/Kp2aKeeShare/Kp2aKeeShare.csproj
src/keepass2android-app/ConfigureKeeShareActivity.cs
src/keepass2android-app/EditKeeShareActivity.cs
src/keepass2android-app/Resources/layout/config_keeshare.xml
src/keepass2android-app/Resources/layout/edit_keeshare.xml
src/keepass2android-app/Resources/layout/keeshare_config_row.xml
src/keepass2android-app/Resources/layout/keeshare_mount_row.xml
src/keepass2android-app/Resources/values/arrays.xml
tests/e2e/keeshare/coverage.md
tests/e2e/keeshare/journey_data.py
tests/e2e/keeshare/local_safety_data.py
tests/e2e/keeshare/make_fixtures.py
tests/e2e/keeshare/two_databases_data.py
tests/e2e/keeshare/verify_share.py
tests/e2e/keeshare_journey.py
tests/e2e/keeshare_local_safety.py
tests/e2e/keeshare_reload.py
tests/e2e/keeshare_search_lock.py
tests/e2e/keeshare_two_databases.py
tests/e2e/test_keeshare_journey.py
tests/e2e/test_keeshare_two_databases.py
docs/features/keeshare-verification.md
```

## Exact review/report index

- T1: [T1-review-1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T1-review-1.md); [T1-review-2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T1-review-2.md)
- T2: [T2-review-1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T2-review-1.md); [T2-review-2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T2-review-2.md)
- T3: [T3-review-1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T3-review-1.md); [T3-review-2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T3-review-2.md)
- T9: [T9-review-1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T9-review-1.md); [T9-review-2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T9-review-2.md)
- T4: [T4-review-1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/38e069c4-1f41-46b2-a21a-8f947abe29cd/keeshare/T4-review-1.md); [T4-review-r2-recovery.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/2b1da684-3f20-41d7-9b13-358e6833f7f2/keeshare/T4-review-r2-recovery.md); [T4-review-r3.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/384faaf1-2d96-4707-b394-198e22c48e2d/keeshare/T4-review-r3.md)
- T5: [T5-review-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/5254e9c8-cbbd-41b1-9bb1-e1af5624227e/keeshare/T5-review-r1.md); [T5-review-r2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/39bc16a4-c15e-4b80-a422-e09f18611df6/keeshare/T5-review-r2.md)
- T6: [T6-review-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/76af1432-0ada-4a43-ae22-e50832342dd3/keeshare/T6-review-r1.md); [T6-review-r2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/3519339f-f894-464e-9c94-de5c242c8ba6/keeshare/T6-review-r2.md)
- T7: [T7-review-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/3cc7c8e1-4de8-42b5-a348-062a3ce57681/keeshare/T7-review-r1.md); [T7-review-r2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/f507f4d2-637c-4ede-93c5-88e89287377c/keeshare/T7-review-r2.md)
- T8 harness: [T8-review-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/afb680ee-a4c8-4a0a-80c3-b239f3b79d05/keeshare/T8-review-r1.md); [T8-review-r2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/8e6e0cb2-de16-4a43-9712-aa843c8dd6d5/keeshare/T8-review-r2.md); [T8-review-r3.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/6b4e9c3b-bc47-4255-abed-8ce1c94bd9bb/keeshare/T8-review-r3.md)
- Repairs1–3: [E2E-repair-1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/457c1e90-e755-45cf-8915-62ebb092af12/keeshare/E2E-repair-1.md); [E2E-repair-2-UTC.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/812304fb-a44f-4af6-b1ce-9276bb6eb3a1/keeshare/E2E-repair-2-UTC.md); [E2E-UTC-repair-review.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/2f8afa2d-3dea-4af3-b58c-f988d6811f81/keeshare/E2E-UTC-repair-review.md); [E2E-repair-3-search-sync.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/bad52502-423f-47f4-a34e-35721264976f/keeshare/E2E-repair-3-search-sync.md); [E2E-repair3-review-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/d6e18450-5f65-4f1b-b1c7-6afba375f179/keeshare/E2E-repair3-review-r1.md); [E2E-repair3-runtime.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/d9834bc6-c826-4006-bf3a-d59a5c4dc4e5/keeshare/E2E-repair3-runtime.md)
- Repair4 source: [E2E-repair-4-reload.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/b7f3ffa5-ce71-4154-b2fb-f5b35baaae59/keeshare/E2E-repair-4-reload.md); [E2E-repair4-review-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/fd4c1c04-ffaf-4391-87ea-3cdcc54d756d/keeshare/E2E-repair4-review-r1.md); [E2E-repair4-fix-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/400f32e8-9903-46cd-823b-193f22cd3b91/keeshare/E2E-repair4-fix-r1.md); [E2E-repair4-review-r2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/191f71a8-b3e7-4bac-92ad-65704a85e320/keeshare/E2E-repair4-review-r2.md); [E2E-repair4-fix-r2.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/4e0f118a-45b5-4e3a-ba6b-0e1a88e18009/keeshare/E2E-repair4-fix-r2.md); [E2E-repair4-review-r3.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/6eea0847-c7e4-4061-97b5-cd7ee6543b21/keeshare/E2E-repair4-review-r3.md)
- Other bounded runtime: [E2E-local-safety-coverage.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/23b836af-e192-479b-9f8b-1cd98b7fcd1b/keeshare/E2E-local-safety-coverage.md); [E2E-local-safety-review-r1.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/82375603-014d-44b8-8ef7-e86d37bbae54/keeshare/E2E-local-safety-review-r1.md); [E2E-reload-recreation.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/7d00c8af-0a7c-4857-8f71-08a5d0e57cea/keeshare/E2E-reload-recreation.md); [E2E-foreground-review.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/b2ae564f-a1c4-4a7b-b7f6-498a58c730ea/keeshare/E2E-foreground-review.md); [E2E-search-lock-confirm.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/cf40d290-27ca-49eb-985c-8aaea8e47c21/keeshare/E2E-search-lock-confirm.md); [ADB-transport-investigation.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/7506d5ad-2796-4170-8777-642b7f9384c3/keeshare/ADB-transport-investigation.md); [ADB-controlled-recovery.md](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/26849f74-f459-4e6a-a688-a89d47539e98/keeshare/ADB-controlled-recovery.md)
