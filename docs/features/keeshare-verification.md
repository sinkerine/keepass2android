# KeeShare verification inventory

## User acceptance with documented residual coverage

After independent acceptance of the original feature gates and final focused runtime cases, the user explicitly chose **Accept with documented residual coverage**. All six additional review groups below are deferred for this delivery: safety/fault injection, export/nesting variants, controlled lifecycle/ownership races, remaining read-only routes, editor/destination variants, and provider/cache variants. They remain unexecuted risks, not passed tests. Live SMB/Samba retains its earlier execution waiver. This acceptance authorizes neither a new commit nor a merge.

The original-gate evidence is accepted as documented in the final focused reconciliation. No known unresolved product finding remains from the completed source reviews. Deferred Minor limitations and repository hygiene notes remain recorded. Earlier text describing acceptance as open is a historical checkpoint superseded by this explicit disposition; raw run failures and not-run records remain unchanged.

## Current status after authorized resume

The user resumed work after the infrastructure mitigation and authorized repair5. **Full feature acceptance and merge approval remain open.** No known unresolved product source finding remains after repair5's independent review. The remaining gates are incomplete evidence and explicit disposition of required review coverage, not a known failing product assertion.

Final APK **G / repair5** is `b50e06bf1e48eb7dd8657610d84f1ceaa89fd31058e3c6fa1680d743b730b8f2` (278,924,175 bytes). Build succeeded (0 errors, 5,112 warnings); parent product tests passed **124 (8 Autofill + 116 KeeShare)** and final Python harness tests passed **54**. The final-G core `run-obajlvsi` passed all ten original steps, engine add/change/delete, wrong-key atomicity and the log audit; `/tmp/keeshare-r5-core-corrected.exit` is **0**.

Final-G local `run-x_es8qeu` passed all seven original bounded cases plus the inactive control. Its **overall exit remains 1**, with **7 behavioral passes and 1 failure**: an added empty-path/current-device IOC case failed picker navigation before Save, leaving that Android combination unverified (P2 / Minor harness finding, not an established product defect). Final-G offline/mount `run-qkg4lay7` passed all four cases, exit0, independently reviewed with no issues. The parent independently hashed retained installed APKs and decrypted persisted outputs from both runs. Full installed bytes, guest hash and stable package paths were verified; a host input hash alone is not provenance.

Repair4 ordinary reload/ownership `run-ips13r52` remains 15 reviewed passes **on predecessor F**, not final-G runtime. G changes only two direction predicates, their explanatory comment and six host cases relative to F's product source. Earlier extended/safety evidence remains attributed to A. Raw `failed`, `running` and `not-run` statuses are preserved; later separate passes do not rewrite them.

The [approved plan](keeshare-plan.md) defines the original 11 criteria and ten steps. [Android coverage](../../tests/e2e/keeshare/coverage.md) records execution slices. The [separate infrastructure report](../e2e-adb-transfer-reliability.md) describes the settled runner and verified-transfer mitigation, **not an emulator/adbd root-cause fix**. Its historical pause and harness-migration statements describe that investigation checkpoint; they do not override the resumed final-G results. Repeated transfer incident history is retained in raw reports rather than repeated here.

## Decisions and scope

- The user approved work directly in the local main worktree, with no additional commits, staging or merge authorized. An existing commit is observed below; its actor is unknown. Base remains the user's environment commit `42e395f99b286b32b919bfd2f6a80c27e860a36a`; preserve its setup, skill, development guide, SDK tooling, runner, ignore rules and Dropbox project line. Additive feature edits to `flake.nix`, `scripts/kp2a` and the business project do not replace that setup.
- PRs #3130 and #3106 were independent design references only. The approved wire format derives from KeePassXC. No source copying is asserted.
- Import, Export and Synchronize, both containers, per-device encrypted IOC/mount data and default-on preferences are approved. SMB support is required; **live SMB/Samba execution alone is explicitly waived**. Build, source status-check review and host path/credential tests remain required.
- Modern Android does not expose the old built-in file browser. Opening only the app-private main fixture through exported `kp2a.action.SelectCurrentDbActivity`, with actual password UI and no password extra, was approved. Device-file choices use the real Downloads document provider. Nonexported Entry/EntryEdit activities were not exposed for testing; a supported in-app seam is needed for direct/stale-intent checks.
- Missing cloud credentials/provider access justifies unavailable execution, not a pass or waiver. The bounded local checks now have G evidence; broader provider checks still require explicit disposition. The user authorized repair4 coalescing and repair5 direction-only eligibility; both source review gates found no remaining issue.

## Build identities and runtime ledger

| Identity | Exact APK SHA256 | Evidence boundary |
|---|---|---|
| A, repair1 | `4207369bb9d2349bd58befdfba55e5735f53fe7b6757d6f472950ca326f9179b` | Earlier core/extended, persisted safety, foreground and preference/recreation evidence only |
| B, repair2 UTC | `6354520724f2a0b456cc367eb746b3face3154fb1daac4c59526a4042287fd90` | Search-lock diagnostic and owner-deletion follow-up context; not final coalescing proof |
| C, repair3 search | `7bc377f6597afdb3851ea18b563a515e47012a2422addd9ff39fa5440342494b` | Search handoff repair; subsequent duplicate-prompt failure retained |
| D, initial repair4 | `aa7c5e2595ce3afb92c20566f3a6a1216e3b7236701fd47678b4bf4f22c571a2` | Intermediate source/build artifact, superseded after review fixes |
| G, final repair5 | `b50e06bf1e48eb7dd8657610d84f1ceaa89fd31058e3c6fa1680d743b730b8f2` | Final source review, build and124 product tests; core, local acceptance and offline/mount runs below |
| F, final repair4 | `98149d7c99a16222d02208a009e27ceaad9d1b2a851a2f609db7671577255216` | Predecessor source review3/build and parent 118 tests; ordinary runtime `run-ips13r52`; predecessor core checkpoint below |

Current G signed APK path: `src/keepass2android-app/bin/Debug/net9.0-android/keepass2android.keepass2android_debug-Signed.apk`. F is 278,924,175 bytes. `.dev/reload-repair4-fix-r2/final-validation.json` records final source/APK hashes, build exit0, 0 errors and 5093 warnings. Parent `/tmp/keeshare-parent-r4-fix2-tests.log` records 8 Autofill + 110 KeeShare passes, no failures/skips. The parent also reported 35 harness tests; the dedicated final runtime worker separately recorded seven provenance/recovery host passes. These gates do not execute Android lifecycle edges.

| Run / identity | Raw outcome and supported evidence | Limit |
|---|---|---|
| `run-obajlvsi` / G | Original10 + engine add/change/delete + wrong-key atomicity passed; log audit passed; exit0 | Extended ledger cases remain not-run in this core run |
| `run-x_es8qeu` / G | Seven original bounded local cases passed: foreign IOC fallback, missing/unresolvable location, imported nested read-only, ordinary and Sync editing, failure continuation, UI removal; inactive control passed | Extra empty-path/current-device IOC picker case failed before Save; overall exit1 retained; checked-state comparisons are bounded |
| `run-qkg4lay7` / G | All4 passed, exit0: real offline skip with local positive control, automatic online recovery, derived mount create/unpicked-peer resolution/removal and persisted checks | Synthetic WebDAV; no live SMB/authentication correctness or cross-device mount isolation claim |
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

## Final focused acceptance reconciliation

Independent review accepted the four final focused gates on G with no Critical/Important findings. `run-tjc6g7gx` proves move-IN refusal for the Import root/subgroup with entire persisted parent byte/tree equality. `run-69jh8qo4` proves normal Export-only edit and independently readable output, including populated KeepGroups=False exclusion and unchanged source subgroup. `run-r357f4eo` proves empty desktop Path with actual UI-selected current-device IOC, imported marker, unchanged inactive control, and no pre-Save writes (exit0). Earlier failed ledgers retain their original exit/status; passes are scoped across these sessions. Parent independently decrypted outputs and hashed the full installed APK from all three against G.

See [final focused review](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/9b06b597-972d-4437-a477-330a6e654485/keeshare/Last-runtime-acceptance-review.md).

Parent acceptance arbitration also closes the original background/pending wiring requirement by inspected trigger/callback composition and shared-path runtime evidence, without claiming every trigger timing ran. G corrupt/wrong-key cases compare **the entire decrypted persisted database**, not merely selected fields. Inspected importer I/O/scratch validation before commit and nested-save failure returning before export support the original failure boundary; unsaved-memory/fault injection remains unexecuted review coverage. With the focused runtime gates above, no original criterion is currently blocked on the stale gap list below. Full feature acceptance remains pending explicit user disposition of the finite additional review matrix, which is not silently waived.

## Original acceptance criteria

“Bounded” identifies the executed portions, not a waiver of other requirements. Host/source gates can establish requirements that do not require live Android or live SMB execution. No live KeePassXC GUI roundtrip is claimed.

| AC | Actual evidence | Remaining original requirement / disposition |
|---|---|---|
| 1 Format | 116 KeeShare host tests, golden codec/reference tests and T1 review2; repair5 preserves codec and IsValid | Host/source gate passed |
| 2 Containers | Host magic/read/write tests; G core plain creation and zip import/export | Original bounded gate passed |
| 3 Import | G core relative open, add/change/delete; A scratch safety/nested controls; F ordinary manual Sync/automatic Both; G online recovery | Background/pending sync trigger and complete outside-group preservation beyond checked fields lack runtime evidence; controlled lifecycle matrix is separately review-added |
| 4 Export | G core save→zip and plain export with pykeepass; A recursive both-format metadata/sanitization and nested config preservation; F automatic Both export | KeepGroups=False subgroup exclusion lacks explicit runtime evidence in the inventory; source/host support does not claim that Android variant passed. Cold convergence/nested deletion controls are review-added |
| 5 Device location | Host precedence/device-key tests; G relative import, foreign IOC ignored with fallback, actual current-device key, missing/unmapped rows and unchanged parent after Sync | Original bounded slice passed. Full two-real-device execution remains broader coverage; extra empty-path/current-device IOC Android combination is unverified after harness failure |
| 6 Read-only | G core Add/Delete/Move negatives; G imported descendants/subgroup/entry no mutation/Edit; actual ordinary and Sync edits persisted | Move into/out of Import targets and Export-group editability remain concrete original evidence gaps; direct/stale/mixed/history/TAN are additional review coverage |
| 7 Nonblocking/safe | Reviewed OperationRunner/locker; G corrupt/wrong-key preservation and failure continuation; A collision controls; F reader release/idle | Failed-import save/I/O boundaries and full database preservation beyond bounded checked state remain unverified; full fault/live-memory/tombstone matrix remains required review coverage |
| 8 Secrets | G core fixture password/private-path log audit; A recursive sanitization; F ordinary logs and source review | Original bounded audit passed; not an exhaustive provider-error/credential audit |
| 9 Config UI | G original7/8/9, local removal with all IOC keys cleared/content kept; G real picker, mount derive/create/peer/remove and missing-location/result states | Original bounded slice passed; all draft/recreation/grant/provider permutations remain additional review coverage |
| 10 SMB | Host UNC/credential/mount/hash policy tests, T9 NTStatus/build/source review; G real nonlocal offline skip, local control and automatic online recovery; G mount picker/peer/removal | Approved build/review/host boundary plus nonlocal runtime slice passed. Live SMB/Samba execution alone is waived; WebDAV does not establish SMB runtime or authentication |
| 11 Tests/build/journey | G build,124 product tests,54 Python tests, original10 core exit0 | Original named gate passed; does not close other original requirements or required review matrix |

**Original gate disposition:** the final focused reconciliation above supersedes the former missing-case entries in this historical table. Original gates are supported by the combined accepted runtime/source/host evidence. Additional controlled timing, fault, and provider requirements below remain unverified and require explicit owner disposition. This is not a claim that every variant ran.

## Original ten-step journey

| Step | Earlier A | Final G |
|---|---|---|
| 1. Prepare | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 2. Password open / groups | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 3. Relative automatic import | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 4. Read-only visible controls | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 5. Zip Synchronize import | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 6. Save and verify zip export | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 7. Configuration rows | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 8. Create Personal export / strip reference | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 9. Picked corrupt file / failed row / unchanged DB | `passed` run-mcumo38o | `passed` run-obajlvsi |
| 10. Secret/private-path log audit | `passed` run-mcumo38o | `passed` run-obajlvsi |

Step2 uses the approved exported open-file route because the original internal browser is absent on Android36. No earlier failure is rewritten by a later pass. Final ordinary two-database secret checks supplement but do not replace original step10's private-path audit.

## Additional review matrix still open

These requirements arose during review and remain separate from the original11/10 mapping. They are required unless the owner explicitly changes acceptance. Only live SMB execution is waived.

- **Safety/import:** different-object-type collision; nonempty existing tombstones; forced save/live-memory collision atomicity; automated comparison of all unrelated outside objects/parents; plain-format safety variants. Existing older/equal/newer descendant and creation-provenance controls have earlier A evidence.
- **Export/nesting:** repeated cold-reopen convergence, Remove sharing timestamp behavior, matching nested deletion staying deleted and stripping newly arriving remote credentials, both formats after those controls. Recursive sanitization, source immutability and local nested config preservation have bounded A passes.
- **Lifecycle/ownership:** controlled finishing-QuickUnlock/pre-OnResume result delivery; lock/background/close/replacement cancellation; late callbacks and GUID stale tokens; current DB switching/two pending targets; rapid taps/fast decisions; rotation/timeout; canceled/failed reopen and unrelated later open; cached instance replacement; AutoOpen completion/cancel, pending sync drain/dedup and selector recreation; reader-acquisition failure. F ordinary route clears its reproduced failure only and remains predecessor-build runtime evidence.
- **Read-only/mutation:** direct stale entry/editor callbacks, mixed/combined/search selections, move/paste/copy guards and editable Export controls, real lock/detached refusal, history/TAN. G supplies bounded imported-descendant and ordinary/Sync editing passes. Nonexported entry activities justify no external-intent launch; they do not waive supported in-app refusal checks.
- **Editor/destination:** password reentry save with B/empty password, repeated recreation/process death, draft IOC/mount retention and saved-state secrecy; rejected read-only/backup/missing-parent local paths; new local destination only after Save; temporary/read-only document grants; no pre-save append/truncate/create/copy/upload across repicking, clearing and mount choices. Existing writable Downloads cancel and recreation cancel have A passes.
- **Offline/providers:** G closes bounded nonlocal offline skip/local control and automatic online recovery; broader cache/cloud behavior remains; OneDrive variants and Google Drive full/app-data new-name rejection/existing-file acceptance with provider operation evidence; ordinary Import picker/copy regression. Credentials/provider access were unavailable. Owner must supply access, accept an explicit deferral, or keep these blocked.

## Review and repair gates

Task source review rounds: T1/T2/T3/T9 each two; T4 three; T5/T6/T7 each two; T8 harness three. Final task source/build gates found no remaining Critical/Important issue; T8's bounded harness gate does not accept missing runtime coverage. Important findings were fixed under parent rulings; T4's recursive credential export finding was Critical and fixed by recursive clone sanitization. T4 subsequent rounds fixed touched clone timestamps, nested local sharing preservation and newer-child placement rejection. T5 fixed stale export before reload; T6 fixed password recreation, owner identity, Copy protection and pre-save/provider selection; T7 fixed lifecycle owner initialization and wrong-clone deletion. T8 fixed installed provenance and stale/empty UI capture negative assertions.

Repair1 initialized the temporary remote database before parsing corrupt headers and removed private destination diagnostics. Repair2 corrected deletion timestamps to UTC after a real serializer assertion, preserving owner routing. Repair3 closes search and releases its lifetime reader before one-shot Sync on a usable resumed host; the API seam and intentional search closure were parent-approved. Its subsequent runtime exposed duplicate reload dialogs. User-authorized repair4 coalesces exact-target requests, strongest Both intent and GUID routing; review1 fixed ordinary-navigation invalidation and UI thread ownership, review2 required retaining changed results across finishing/pre-resume handoff, review3 cleared source. The later F ordinary route and independent runtime review passed within their stated boundaries.

Repair5, explicitly authorized after resume, removes the desktop-path condition from IsImporting/IsExporting so active unresolved references reach location resolution and record Skipped; Inactive remains ineligible. Six host cases verify direction/codec and IOC precedence. Independent source review found no issues. G local runtime verifies missing-location/inactive behavior; the added empty-path/current-device IOC case remains unverified at the picker boundary.

Deferred Minor findings and limits:

- Export rejection dialog rotation can leave a blank picker; system Back recovers. T6 review2 explicitly deferred this.
- SMB CloseFile failure can mask an earlier I/O error; T9 notes remain report-only, live failure handling not executed.
- Local safety startup before recorder initialization produced no JSON or useful pull stderr for run-gxw9prqf; deferred Minor, behavior unverified.
- F ordinary postdecision samples assert fresh XML at runtime but do **not** retain each XML: only activity/window samples and final XML remain. Do not call these durable per-sample XML artifacts.
- Long-list zero-row XML versus harness scrolling remains unexplained (run10/11/14/16-era failures; run-6blgs11a rendered rows during investigation). No product defect or source repair attribution established.
- ADB/emulator internal root cause remains unresolved; settled startup and shared verified-transfer recovery mitigate observed trigger windows. This is separate infrastructure evidence.
- P2 / Minor: G added empty-path/current-device IOC picker navigation fails before Save; no product defect established. Seven original local passes remain valid; overall exit1 is retained.

## Final review handoff

Consolidated final review/disposition is the next step. Resolve the specific original evidence gaps above, the extra picker regression, and the required review-added matrix explicitly; do not silently downgrade them to optional work or infer a waiver. Provider access and supported in-app seams still need owner disposition. This inventory does not authorize further feature changes, testing campaigns, staging, commits or merge, and does not grant feature completion approval.

## Final working-tree inventory

The preserved environment base is `42e395f99b286b32b919bfd2f6a80c27e860a36a`. Actual observed HEAD is **`b871ec76`**, its child, with implementation and infrastructure already committed. The actor is unknown; no additional commit was made by this documentation task or the parent. Preserve this commit: no reset/amend is authorized. The main-local exception persists. Base setup remains preserved with additive feature/infrastructure changes called out separately below; it is not accurate to describe the whole delivery as uncommitted.

Relative-to-base inventory includes tracked additions and remaining untracked files. Status letters below describe differences from base, not current untracked status. Generated evidence under ignored `.dev/` and external session reports remains outside delivery source.

Feature/product, resources, tests and documentation relative to base:

```text
A	docs/features/keeshare-plan.md
A	docs/features/keeshare-verification.md
M	flake.nix
M	scripts/kp2a
M	src/KeePass.sln
R100	src/keepass2android-app/app/NoFileStorageFoundException.cs	src/Kp2aBusinessLogic/Io/NoFileStorageFoundException.cs
M	src/Kp2aBusinessLogic/Io/SmbFileStorage.cs
A	src/Kp2aBusinessLogic/KeeShare/KeeShareExporter.cs
A	src/Kp2aBusinessLogic/KeeShare/KeeShareGroups.cs
A	src/Kp2aBusinessLogic/KeeShare/KeeShareImporter.cs
A	src/Kp2aBusinessLogic/KeeShare/KeeShareLocationResolver.cs
A	src/Kp2aBusinessLogic/KeeShare/KeeShareScheduler.cs
A	src/Kp2aBusinessLogic/KeeShare/KeeShareSyncOperation.cs
M	src/Kp2aBusinessLogic/Kp2aBusinessLogic.csproj
M	src/Kp2aBusinessLogic/OperationRunner.cs
M	src/Kp2aBusinessLogic/PreferenceKey.cs
M	src/Kp2aBusinessLogic/SelectStorageLocationActivityBase.cs
M	src/Kp2aBusinessLogic/UiStringKey.cs
M	src/Kp2aBusinessLogic/database/CheckDatabaseForChanges.cs
M	src/Kp2aBusinessLogic/database/edit/DeleteRunnable.cs
M	src/Kp2aBusinessLogic/database/edit/SaveDB.cs
A	src/Kp2aKeeShare.Tests/KeeShareContainerTests.cs
A	src/Kp2aKeeShare.Tests/KeeShareMountMapTests.cs
A	src/Kp2aKeeShare.Tests/KeeSharePathTests.cs
A	src/Kp2aKeeShare.Tests/KeeShareReferenceTests.cs
A	src/Kp2aKeeShare.Tests/KeeShareSmbPathTests.cs
A	src/Kp2aKeeShare.Tests/KeeShareTreeFingerprintTests.cs
A	src/Kp2aKeeShare.Tests/Kp2aKeeShare.Tests.csproj
A	src/Kp2aKeeShare/KeeShareContainer.cs
A	src/Kp2aKeeShare/KeeShareMountMap.cs
A	src/Kp2aKeeShare/KeeSharePath.cs
A	src/Kp2aKeeShare/KeeShareReference.cs
A	src/Kp2aKeeShare/KeeShareSmbPath.cs
A	src/Kp2aKeeShare/KeeShareTreeFingerprint.cs
A	src/Kp2aKeeShare/Kp2aKeeShare.csproj
A	src/keepass2android-app/ConfigureKeeShareActivity.cs
A	src/keepass2android-app/EditKeeShareActivity.cs
M	src/keepass2android-app/EntryActivity.cs
M	src/keepass2android-app/EntryEditActivity.cs
M	src/keepass2android-app/GroupActivity.cs
M	src/keepass2android-app/GroupBaseActivity.cs
A	src/keepass2android-app/Resources/layout/config_keeshare.xml
A	src/keepass2android-app/Resources/layout/edit_keeshare.xml
M	src/keepass2android-app/Resources/layout/group.xml
A	src/keepass2android-app/Resources/layout/keeshare_config_row.xml
A	src/keepass2android-app/Resources/layout/keeshare_mount_row.xml
M	src/keepass2android-app/Resources/menu/group_entriesselected.xml
A	src/keepass2android-app/Resources/values/arrays.xml
M	src/keepass2android-app/Resources/values/strings.xml
M	src/keepass2android-app/Resources/xml/pref_app_file_handling.xml
M	src/keepass2android-app/Resources/xml/pref_database.xml
M	src/keepass2android-app/SelectCurrentDbActivity.cs
M	src/keepass2android-app/SelectStorageLocationActivity.cs
M	src/keepass2android-app/SyncUtil.cs
M	src/keepass2android-app/app/App.cs
M	src/keepass2android-app/search/SearchResults.cs
A	tests/e2e/keeshare/coverage.md
A	tests/e2e/keeshare/journey_data.py
A	tests/e2e/keeshare/local_acceptance_data.py
A	tests/e2e/keeshare/local_safety_data.py
A	tests/e2e/keeshare/make_fixtures.py
A	tests/e2e/keeshare/two_databases_data.py
A	tests/e2e/keeshare/verify_share.py
A	tests/e2e/keeshare_journey.py
A	tests/e2e/keeshare_local_acceptance.py
A	tests/e2e/keeshare_local_safety.py
A	tests/e2e/keeshare_reload.py
A	tests/e2e/keeshare_search_lock.py
A	tests/e2e/keeshare_two_databases.py
A	tests/e2e/test_keeshare_journey.py
A	tests/e2e/test_keeshare_local_acceptance.py
A	tests/e2e/test_keeshare_two_databases.py
```

Separate infrastructure relative to base:

```text
M	docs/development.md
A	docs/e2e-adb-transfer-reliability.md
A	tests/e2e/adb_transfer.py
A	tests/e2e/adb_transfer_stress.py
M	tests/e2e/run.py
A	tests/e2e/test_adb_transfer.py
```

Generated artifacts already in observed HEAD (cleanup risk):

```text
A	tests/e2e/__pycache__/adb_transfer.cpython-313.pyc
A	tests/e2e/__pycache__/keeshare_local_acceptance.cpython-313.pyc
A	tests/e2e/keeshare/__pycache__/journey_data.cpython-313.pyc
A	tests/e2e/keeshare/__pycache__/local_acceptance_data.cpython-313.pyc
A	tests/e2e/keeshare/__pycache__/make_fixtures.cpython-313.pyc
```

Current working changes against observed HEAD (plus these two documentation edits):

```text
M src/Kp2aKeeShare/KeeShareReference.cs
M src/Kp2aKeeShare.Tests/KeeShareReferenceTests.cs
M src/Kp2aKeeShare.Tests/KeeSharePathTests.cs
M tests/e2e/keeshare/local_acceptance_data.py
M tests/e2e/keeshare_local_acceptance.py
M tests/e2e/test_keeshare_local_acceptance.py
?? tests/e2e/keeshare/offline_mount_data.py
?? tests/e2e/keeshare_offline_mount.py
```

The five committed pycache artifacts are a concrete delivery cleanup risk; this documentation-only task does not remove them. Infrastructure is separately owned and preserved, including any concurrent uncommitted changes; none was edited here. The index is empty at documentation validation. No feature/test/resource scripts are omitted merely because they were untracked at an earlier checkpoint.

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

- Repair5: [implementation](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/6ad11748-6260-4391-aedb-09206905eac9/keeshare/E2E-repair5-empty-location.md); [source review](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/82de2218-6d94-41de-80e0-4d961b873ee4/keeshare/E2E-repair5-review.md); [local runtime review](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/87ec5bf1-3bd9-40e2-8bd2-432b35a8b3a7/keeshare/E2E-repair5-local-review.md). The local review's then-running core statement is superseded only by the separately recorded completed G core.
- Final-G [offline/mount runtime review](/home/sinkerine/.pi/agent/sessions/--home-sinkerine-dev-keepass2android--/subagent-artifacts/outputs/60fd1fac-b323-48bf-b0e4-bab48cce5436/keeshare/E2E-offline-mount-review.md); `.dev/e2e/run-qkg4lay7/keeshare/independent-offline-mount-verification.json` and `.dev/e2e/run-x_es8qeu/keeshare/independent-output-readback.json` retain bounded persisted verification.
