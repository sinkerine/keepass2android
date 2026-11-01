# KeeShare support — implementation plan

Status: **approved by the user**. Every *(default)* decision below was confirmed by the
user, and so were these: SMB credentials are stored the way KeeAutoExec stores them today
(inside the encrypted db), and the e2e journey for SMB/Samba is skipped.

Reference: closed PR #3130 and open PR #3106 were read for ideas only. Nothing is copied
from them. The wire format below comes from KeePassXC `src/keeshare/*` (current `develop`).

## 1. Goal and acceptance criteria

### Goal

Keepass2Android (KP2A) can use KeePassXC KeeShare groups. A group carrying KeePassXC's
`KeeShare/Reference` is imported from, exported to, or synchronized with a separate
share file. On each device, the user can point the share at a file through KP2A's normal
storage picker. Users can also create and edit KeeShare groups in KP2A, and KeePassXC
reads the result.

### Scope decisions

| Topic | Decision |
|---|---|
| Directions | Import, Export and Synchronize (Import+Export) *(default)* |
| Containers | Read `.kdbx` and `.kdbx.share` (zip; signature file ignored, as KeePassXC does today). Write `.kdbx`; write `.kdbx.share` as a zip that holds only `container.share.kdbx` *(default)* |
| Signatures / trust store | Not implemented. KeePassXC no longer verifies signatures on import, so a KP2A trust store would offer no interop value *(default)* |
| Configuration UI | Full create/edit/remove of references plus a per-device file location *(default)* |
| Credential storage | Like KeeAutoExec today: per-device IOCs, including `smb://user:pass@…`, live in the encrypted db's CustomData *(user-confirmed)* |
| Per-device location | Group CustomData `KP2A/KeeShare/Ioc/<ThisDeviceId>` (serialized `IOConnectionInfo`), travels with the db *(default)*. Fallback: a relative `Reference.Path` resolved against the database's parent folder via `IFileStorage` |
| SMB share files | **Required (user).** Share files may live on SMB servers through KP2A's built-in `SmbFileStorage` (Net/Debug flavors). KeePassXC references that use a desktop **mount path** (`/mnt/nas/…`, `Z:\…`) or a **UNC path** (`\\nas\share\…`, `//nas/share/…`, `smb://nas/share/…`) resolve on Android through per-device mount mappings, or through automatic UNC translation (§2.4 "Location resolution") |
| Global switches | App preferences "KeeShare import" and "KeeShare export", both default **on** (mirrors KeePassXC's `KeeShare/Active`) |
| Non-goals (v1) | Signing exports; signer trust UI; resolving `{REF:…}` placeholders that point outside the share (KeePassXC does this on export); periodic background job (we reuse the existing open/sync/save triggers); renaming "Child databases" translations other than English |

### Acceptance criteria

1. **Format compatibility.** `KeeShareReferenceCodec` decodes KeePassXC-encoded references
   (golden strings in tests). This includes references without `KeepGroups`, which then default
   to `false`. Encoding produces XML that KeePassXC's `Reference::deserialize` accepts:
   element names `KeeShare/Type/{Import,Export}/Group/Path/Password/KeepGroups`, base64 fields,
   `KeepGroups` as `True`/`False`, and the group uuid as 16 raw bytes in RFC-4122 order, which
   equals `PwUuid.UuidBytes`.
2. **Containers.** A `.kdbx.share` zip is read by extracting the `container.share.kdbx` entry.
   Detection uses the zip magic bytes, not the file name, as KeePassXC does. A plain KDBX is
   read as is. Exported `.kdbx.share` files are zips containing `container.share.kdbx`.
3. **Import.** Opening a database, or a manual or background sync, imports each active
   Import/Synchronize share into its group. Entries added, changed or deleted in the share
   file appear, change or disappear in the group. Nothing outside the shared group changes,
   apart from custom icons and deleted-object records. The group's own name, icon, notes and
   CustomData are kept.
4. **Export.** After a successful save, every active Export/Synchronize share whose subtree
   changed is written to its file. Synchronize shares import first. The written file opens in
   KeePassXC/pykeepass with the share password. Its root contains the group's entries, plus
   subgroups only when `KeepGroups=True`. It carries no `KeeShare/Reference` and no
   `KP2A/KeeShare/*` keys.
5. **Per-device location.** A location chosen on device A is stored under A's device id and
   is ignored on device B. With no device location and a relative `Reference.Path`, the file
   is resolved next to the database through `IFileStorage.GetParentPath`/`GetFilePath`.
   With neither, the share reports "location not set on this device" and is skipped.
6. **Read-only import groups.** Contents of an Import-only share group, and of its
   subgroups, cannot be added to, edited, deleted, or moved into or out of in the UI.
   Synchronize and Export groups stay editable.
7. **Non-blocking and safe.** All KeeShare work runs as `OperationWithFinishHandler`
   operations on `OperationRunner` (non-blocking), never via `Task.Run`. Modifications are
   bracketed by `BackgroundDatabaseModificationLocker`. Each share's failure is reported
   without aborting the others, and a failed import never modifies the database.
8. **No secret leakage.** Logs and messages identify files only through
   `IFileStorage.GetDisplayName(ioc)` and groups by name. `ioc.Path`, share passwords and
   serialized IOCs are never logged.
9. **Config UI.** Database settings → "KeeShare groups" lists shared groups with type, this
   device's location (display name) or "not set", and the last result. From a group's
   long-press menu ("KeeShare…") the user can create, edit or remove a reference and pick
   this device's file through `SelectStorageLocationActivity`.
10. **SMB.** Several share behaviours must hold with share files on an SMB server:
    - **Import and export.** Both work against a file on SMB (code paths reviewed; no
      Samba e2e, which the user skipped). Export uses `OpenWriteTransaction`. When file transactions are on, a failed
      SMB rename surfaces as a `Failed` result, not as success.
    - **Mount mapping.** A reference whose `Path` is a desktop mount path (e.g.
      `/mnt/nas/keeshare/team.kdbx`) resolves through a per-device mount mapping
      `/mnt/nas` → `smb://…@host/share`. Picking the SMB file for one share can create
      that mapping, after which another share under `/mnt/nas` resolves with no further
      picking.
    - **UNC translation.** A UNC or `smb://` reference path resolves automatically when the
      main database is on SMB on the same host, reusing its credentials. Otherwise the
      share reports "SMB credentials needed – pick the file once".
    - **Missing file.** A missing SMB file is reported as "share file not found", not as a
      generic error.
    - **Offline mode.** In KP2A offline mode, non-local shares are skipped with the reason
      "offline" and no network access.
    - **Unchanged files.** Unchanged share files are not decrypted or merged. The content
      hash is compared first, which matters because SMB has no fast change detection.
    - **No credential leakage.** SMB credentials never appear in logs or messages. Only
      `GetDisplayName` is used, which is `smb://host/share/path` without user or password.
11. Host unit tests, the APK build and the e2e journey (section 5) all pass.

## 2. Design

### 2.1 Module boundaries

```
src/Kp2aKeeShare/               net8.0, no Android/KeePassLib deps (host-testable)
  KeeShareReference.cs           model + codec (KeePassXC wire format)
  KeeShareContainer.cs           .kdbx / .kdbx.share (zip) read/write
  KeeSharePath.cs                pure location policy (device ioc / mount map / UNC / relative)
  KeeShareMountMap.cs            per-device desktop-prefix -> folder-ioc mappings (codec + match + derive)
  KeeShareSmbPath.cs             UNC/smb parsing and credential borrowing (string-level, no SMBLibrary)
  KeeShareTreeFingerprint.cs     order-independent fingerprint over (uuid, parent, ticks) tuples
src/Kp2aKeeShare.Tests/          xunit, net8.0
src/Kp2aBusinessLogic/KeeShare/  net9.0-android, uses KeePassLib + IFileStorage
  KeeShareGroups.cs              find/read/write references & device iocs on PwGroup
  KeeShareLocationResolver.cs    KeeSharePath -> IOConnectionInfo using IFileStorage
  KeeShareImporter.cs            load share file, subtree merge
  KeeShareExporter.cs            build export PwDatabase, write via write transaction
  KeeShareSyncOperation.cs       OperationWithFinishHandler running import/save/export
  KeeShareScheduler.cs           coalescing enqueue onto OperationRunner + result cache
src/keepass2android-app/
  ConfigureKeeShareActivity.cs   list of shares (pattern: ConfigureChildDatabasesActivity)
  EditKeeShareActivity.cs        create/edit/remove one reference, pick device file
  hooks in SaveDB.cs, SyncUtil.cs, SelectCurrentDbActivity.cs, Group/Entry activities
src/Kp2aBusinessLogic/Io/SmbFileStorage.cs   hardening only (not-found mapping, rename status, handle close)
```

`Kp2aBusinessLogic.csproj` gets a `ProjectReference` to `Kp2aKeeShare`, and the app picks
it up transitively. The library follows the `Kp2aAutofillParser` pattern (net8.0, consumed
by the Android projects). Namespace for all new code: `keepass2android.KeeShare`.

### 2.2 Wire format (KeePassXC)

- Group CustomData key `KeeShare/Reference`, value `base64(utf8(xml))`:
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <KeeShare><Type><Import/><Export/></Type><Group>b64(16 uuid bytes)</Group>
  <Path>b64(utf8 path)</Path><Password>b64(utf8 pw)</Password><KeepGroups>True</KeepGroups></KeeShare>
  ```
  Type: neither element present = Inactive; Import only; Export only; both = Synchronize.
  An invalid or empty reference is treated as "not shared" and is never thrown on.
  Unknown elements are ignored.
- `.kdbx.share`: zip containing `container.share.kdbx` (the KDBX) and optionally
  `container.share.signature` (ignored on read, not written).
- Share KDBX key: a composite key containing only a password key built from
  `Reference.Password`. The key is present even when the password is the empty string,
  which matches KeePassXC's `PasswordKey("")`, so KP2A uses `new KcpPassword("")`.
- KeePassXC export: the root is a clone of the shared group with its Reference cleared,
  its entries, its subgroups only if KeepGroups, all deleted objects of the source db, and
  the metadata name set to the group name.
- A relative `Path` is resolved against the database file's directory.

### 2.3 Interfaces (exact signatures)

`src/Kp2aKeeShare`:

```csharp
namespace keepass2android.KeeShare;

[Flags] public enum KeeShareType { Inactive = 0, Import = 1, Export = 2, Synchronize = Import | Export }

public sealed record KeeShareReference(
    KeeShareType Type, byte[] GroupUuid, string Path, string Password, bool KeepGroups)
{
    public bool IsImporting { get; }   // (Type & Import) != 0 && Path != ""
    public bool IsExporting { get; }   // (Type & Export) != 0 && Path != ""
    public bool IsValid { get; }       // Type != Inactive && Path != ""
}

public static class KeeShareReferenceCodec
{
    public const string CustomDataKey = "KeeShare/Reference";
    public static bool TryDecode(string customDataValue, out KeeShareReference reference);
    public static string Encode(KeeShareReference reference);           // base64 of xml
}

public enum KeeShareContainerKind { Kdbx, Zip }

public static class KeeShareContainer
{
    public const string ZipDatabaseEntryName = "container.share.kdbx";
    public const string ZipSignatureEntryName = "container.share.signature";
    public static KeeShareContainerKind KindForWrite(string fileNameOrPath); // ".kdbx.share" (ci) -> Zip
    public static byte[] ExtractDatabase(byte[] containerBytes);           // zip magic -> entry, else as-is
    public static byte[] WrapForWrite(byte[] kdbxBytes, KeeShareContainerKind kind);
}
// ExtractDatabase throws KeeShareFormatException("zip has no container.share.kdbx") when needed.
public sealed class KeeShareFormatException(string message) : Exception(message);

public abstract record KeeShareLocation
{
    public sealed record DeviceIoc(string SerializedIoc) : KeeShareLocation;
    public sealed record Mapped(string SerializedFolderIoc, IReadOnlyList<string> Segments) : KeeShareLocation;
    public sealed record Unc(string Host, string Share, IReadOnlyList<string> Segments) : KeeShareLocation;
    public sealed record RelativeToDatabase(IReadOnlyList<string> Segments) : KeeShareLocation;
    public sealed record NotSet : KeeShareLocation;
}

public static class KeeSharePath
{
    public const string DeviceIocKeyPrefix = "KP2A/KeeShare/Ioc/";
    public static string DeviceIocKey(string deviceId);
    // Splits a desktop path into segments: '\\' -> '/', drops empty and "." segments, rejects "..".
    public static IReadOnlyList<string> Segments(string path);
    // Absolute = starts with '/', '\\', "X:", or contains "://".
    public static bool IsAbsolute(string path);
    // Windows-style (drive letter or UNC) paths compare case-insensitively; others case-sensitively.
    public static bool IsWindowsStyle(string path);
    // Order: device ioc > longest mount-map prefix > UNC/smb path > relative path > NotSet.
    public static KeeShareLocation Choose(string? deviceIocValue, string referencePath, KeeShareMountMap mounts);
}

public sealed class KeeShareMountMap
{
    public const string DatabaseCustomDataKeyPrefix = "KP2A/KeeShare/Mounts/"; // + deviceId, on PwDatabase.CustomData
    public sealed record Mount(string DesktopPrefix, string SerializedFolderIoc);
    public IReadOnlyList<Mount> Mounts { get; }
    public static KeeShareMountMap Decode(string? value);   // null/invalid -> empty; one mount per line: b64(prefix) '\t' b64(ioc)
    public string Encode();
    public KeeShareMountMap With(Mount mount);              // replaces an equal prefix
    public KeeShareMountMap Without(string desktopPrefix);
    // Longest prefix matching at a segment boundary; returns remaining segments.
    public bool TryMatch(string referencePath, out Mount mount, out IReadOnlyList<string> remainingSegments);
    // Given an absolute reference path and the segments of a picked file (display path, no credentials),
    // finds the longest common trailing run (>= 1, file name must match, compared per IsWindowsStyle).
    // Returns the desktop prefix and how many GetParentPath steps lead from the picked file to the mapped folder.
    public static bool TryDerive(string referencePath, IReadOnlyList<string> pickedSegments,
                                 out string desktopPrefix, out int parentSteps);
}

public static class KeeShareSmbPath
{
    // "\\host\share\a\b", "//host/share/a/b", "smb://host/share/a/b" (no credentials) -> parts.
    public static bool TryParseUnc(string referencePath, out string host, out string share, out IReadOnlyList<string> segments);
    // If dbIocPath is "smb://<cred>@host/share/..." with the same host (case-insensitive), returns
    // "smb://<cred>@host/share/seg1/seg2" reusing the credential part verbatim; otherwise null.
    public static string? BorrowCredentials(string dbIocPath, string host, string share, IReadOnlyList<string> segments);
}

public static class KeeShareTreeFingerprint
{
    // Each tuple: (uuidHex, parentUuidHex, lastModTicks, locationChangedTicks, historyCount).
    // Root itself is excluded by the caller; result is order-independent SHA-256 hex.
    public static string Compute(IEnumerable<(string Uuid, string Parent, long LastMod, long LocChanged, int History)> items);
}
```

`src/Kp2aBusinessLogic/KeeShare`:

```csharp
public sealed class KeeShareGroup
{
    public Database Database { get; }
    public PwGroup Group { get; }
    public KeeShareReference Reference { get; }
}

public static class KeeShareGroups
{
    public static IReadOnlyList<KeeShareGroup> Find(Database db);           // all groups with a decodable reference
    public static KeeShareGroup? FindShareFor(Database db, PwGroup group);  // nearest ancestor-or-self share
    public static bool IsReadOnlyContent(Database db, PwGroup group);       // inside Import-only share
    // true if any item (or its parent group) or the target group is read-only content
    public static bool BlocksModification(Database db, IEnumerable<IStructureItem> items, PwGroup? target);
    public static void SetReference(PwGroup group, KeeShareReference reference); // also touches LastModificationTime
    public static void RemoveReference(PwGroup group);                     // removes Reference + all KP2A/KeeShare/* keys
    public static IOConnectionInfo? GetDeviceIoc(PwGroup group, string deviceId);
    public static void SetDeviceIoc(PwGroup group, string deviceId, IOConnectionInfo? ioc); // null clears
}

public enum KeeShareLocationProblem { None, NotSet, SmbCredentialsNeeded, StorageUnavailable, Offline }

public static class KeeShareLocationResolver
{
    // Never throws for unresolvable paths; returns null ioc plus the problem.
    public static IOConnectionInfo? Resolve(IKp2aApp app, KeeShareGroup share, string deviceId,
                                            out KeeShareLocationProblem problem);
    public static KeeShareMountMap GetMounts(Database db, string deviceId);
    public static void SetMounts(Database db, string deviceId, KeeShareMountMap mounts); // marks db modified
}

public enum KeeShareOutcome { Unchanged, Imported, Exported, ImportedAndExported, Skipped, Failed }
public sealed record KeeShareItemResult(PwUuid GroupUuid, string GroupName, KeeShareOutcome Outcome, string? Message);

public static class KeeShareImporter
{
    // Returns true if the db subtree changed. Throws on read/parse/key errors (db untouched).
    public static bool Import(IKp2aApp app, KeeShareGroup share, IOConnectionInfo ioc, IKp2aStatusLogger logger);
}

public static class KeeShareExporter
{
    public static void Export(IKp2aApp app, KeeShareGroup share, IOConnectionInfo ioc, IKp2aStatusLogger logger);
}

[Flags] public enum KeeShareSyncMode { Import = 1, Export = 2, Both = 3 }

public class KeeShareSyncOperation : OperationWithFinishHandler
{
    public KeeShareSyncOperation(IKp2aApp app, Database db, KeeShareSyncMode mode,
                                 OnOperationFinishedHandler operationFinishedHandler);
    public IReadOnlyList<KeeShareItemResult> Results { get; }
    public override void Run();
}

public static class KeeShareScheduler
{
    // Coalesces: if a not-yet-started op for db is queued, ORs the mode into it; else enqueues a new
    // KeeShareSyncOperation on OperationRunner.Instance (non-blocking). No-op if db has no active shares
    // or the respective global preference is off.
    public static void Enqueue(IKp2aApp app, Database db, KeeShareSyncMode mode);
    public static KeeShareItemResult? LastResult(Database db, PwUuid groupUuid); // for the config UI
    public static string DeviceId { get; set; }  // set once by the app to KeeAutoExecExt.ThisDeviceId
    public static Func<bool> IsOffline { get; set; } = () => false; // set by the app to () => App.Kp2a.OfflineMode
}
```

Additions to existing types:

- `SaveDb`: `public bool SkipKeeShareExport { get; set; }` (default false). In
  `FinishWithSuccess()`, unless the flag is set, call
  `KeeShareScheduler.Enqueue(_app, _db, KeeShareSyncMode.Export)` after any subsequent
  `SynchronizeCachedDatabase` has been enqueued. The FIFO queue therefore exports after the sync.
- `SmbFileStorage` hardening (no API change):
  - `OpenFileForRead` throws `FileNotFoundException` for `STATUS_OBJECT_NAME_NOT_FOUND`
    and `STATUS_OBJECT_PATH_NOT_FOUND`.
  - The rename in `CommitWrite` checks the `SetFileInformation` status and throws on
    failure, then deletes the temp file on a best-effort basis.
  - Read, write and rename handles are closed with `CloseFile` before the connection is
    disposed.
  - Exception messages use `GetPathWithoutCredentials()`/`LocalPath` only. They already do
    this today, and that must stay true.
- `PreferenceKey`: `keeshare_import_enabled`, `keeshare_export_enabled` (default true).
- `UiStringKey`: `KeeShareImporting`, `KeeShareExporting`, `KeeShareLocationNotSet`,
  `KeeShareWrongPassword`, `KeeShareFileNotFound`, `KeeShareImportedChanges`,
  `KeeShareFailed`, `KeeShareDatabaseReadOnly`, `KeeShareSmbCredentialsNeeded`,
  `KeeShareOffline`, `KeeShareStorageUnavailable`, `KeeShareRememberMount`. Each name equals a `Resource.String` name,
  because `App.GetResourceString` looks them up via reflection.

### 2.4 Data flow

**Triggers** (all go through `KeeShareScheduler.Enqueue`):

| Event | Where | Mode |
|---|---|---|
| Database opened, no background sync pending for it | `SelectCurrentDbActivity` `ReqCodeOpenNewDb` OK branch | Import |
| Sync finished (manual menu, background, pending) | `SyncUtil.StartSynchronizeDatabase` finished handler, next to the OTP aux chain; only on success | Both |
| Save succeeded | `SaveDb.FinishWithSuccess` | Export |

**Location resolution** (`KeeShareLocationResolver.Resolve`, policy in `KeeSharePath.Choose`):

1. **Device IOC.** The group CustomData `KP2A/KeeShare/Ioc/<deviceId>` is unserialized
   with `IOConnectionInfo.UnserializeFromString`. This covers any storage, SMB included,
   picked through `SelectStorageLocationActivity` and its SMB dialog.
2. **Mount mapping.** `PwDatabase.CustomData["KP2A/KeeShare/Mounts/<deviceId>"]` is
   matched by the longest `DesktopPrefix` against `Reference.Path`. Starting from the
   folder IOC, apply `fs.GetFilePath(cur, seg)` once per remaining segment, using
   `fs = app.GetFileStorage(folderIoc, allowCache: false)`. `SmbFileStorage.GetFilePath`
   carries the credentials along.
3. **UNC/`smb://` path.** `KeeShareSmbPath.BorrowCredentials(db.Ioc.Path, …)` is used when
   the main db is `smb://` on the same host. Otherwise the problem is
   `SmbCredentialsNeeded`.
4. **Relative path.** Apply `GetFilePath` from `GetParentPath(db.Ioc)` once per segment.
   This works for local, SMB and other storages that implement both; storages that throw
   (for example some SAF `content://` providers) yield `NotSet`.
5. Otherwise `NotSet`.

Afterwards there are two more checks:
- If the resolved IOC is not local (`!ioc.IsLocalFile()`) and `KeeShareScheduler.IsOffline()`
  is true, the problem is `Offline` and nothing is accessed.
- `NoFileStorageFoundException`, e.g. `smb://` in the NoNet flavor, maps to
  `StorageUnavailable`.

**`KeeShareSyncOperation.Run()`**:
1. `StatusLogger.UpdateMessage(KeeShareImporting/Exporting)`. Read the shares via
   `KeeShareGroups.Find(db)` and resolve each location. Shares with any location problem
   are recorded as `Skipped` with the matching string, and no error toast is shown. The
   config UI shows this status.
2. **Import phase.** This runs for each importing share when the mode has Import, and also
   for Synchronize shares when the mode is Export, so local edits never overwrite newer
   remote ones. Steps:
   - `modificationWatcher.BeforeModifyDatabases()` with a `BackgroundDatabaseModificationLocker`.
   - `KeeShareImporter.Import`.
   - `AfterModifyDatabases()` in a `finally` block.
3. If anything changed and `db.CanWrite`, run a nested `SaveDb` synchronously with
   `SkipKeeShareExport = true`, `DoNotSetStatusLoggerMessage = true` and the operation's
   status logger. This mirrors how `SynchronizeCachedDatabase` nests `SaveDb`. Then post
   `db.UpdateGlobals(); app.MarkAllGroupsAsDirty()` to the UI thread. If `!db.CanWrite`,
   keep the merge in memory and record `KeeShareDatabaseReadOnly`, with no save and no export.
4. **Export phase.** This runs for exporting shares when the mode has Export or the import
   phase changed the db. A share is exported only if its subtree fingerprint differs from
   the last fingerprint read or written for `(db.Ioc serialized, group uuid)`. That state is
   kept in memory in `KeeShareScheduler` and is empty after process start, so the first
   trigger always exports.
5. `Finish(success: no item Failed, message)`. The message is null when every item is
   Unchanged or Skipped. Otherwise it reads, for example, "KeeShare: imported changes into
   ‹Team›" or "KeeShare: ‹Team› failed: ‹reason›". The caller's handler shows it with
   `App.Kp2a.ShowMessage` at the matching severity.

**Import algorithm (subtree merge with `PwDatabase.MergeIn`).** No custom merge code:
1. Open with `app.GetFileStorage(ioc, allowCache: false).OpenFileForRead(ioc)` and read all
   bytes. A failure throws, and the result maps `FileNotFoundException` to
   `KeeShareFileNotFound`. Then compute the SHA-256 of the raw bytes. If it equals the
   last-seen hash for `(db, group)` and the last-seen fingerprint equals the current
   subtree fingerprint, return false without decrypting. SMB and many other storages have
   no fast change detection (`CheckForFileChangeFast` is always false), so this avoids a
   KDF run on every trigger. Then call `KeeShareContainer.ExtractDatabase`.
2. `remote = new PwDatabase(); remote.MasterKey = CompositeKey{ KcpPassword(ref.Password) }`
   and `new KdbxFile(remote).Load(ms, KdbxFormat.Default, null)`. An
   `InvalidCompositeKeyException` maps to `KeeShareWrongPassword`. Rewrite
   `remote.RootGroup.Uuid = share.Group.Uuid`.
3. `scratch.New(new IOConnectionInfo(), remote.MasterKey, "keeshare")`, then
   `scratch.RootGroup = share.Group.CloneDeep()` (uuids preserved).
   Copy `remote.CustomIcons` and `db.CustomIcons` into `scratch` by uuid.
4. `fpBefore = fingerprint(share.Group)` (root excluded), then
   `scratch.MergeIn(remote, PwMergeMethod.Synchronize, null)`.
5. If `fingerprint(scratch.RootGroup) == fpBefore`, return false.
6. Otherwise, under the lock, replace `share.Group`'s child groups and entries with
   `scratch.RootGroup`'s, re-parenting them with `AddGroup/AddEntry(…, true, true)`.
   The share group's own properties stay. For each uuid present before and absent now,
   add a `PwDeletedObject(uuid, DateTime.UtcNow)` to `db.KpDatabase.DeletedObjects` so the
   deletion propagates through KP2A's normal db sync. Add the custom icons referenced by the
   new subtree that `db` lacks. Return true.
7. Store `fingerprint(remote.RootGroup)` (root excluded) as the share's
   last-seen fingerprint.

Merging into a scratch copy confines effects to the shared group. KeePassXC exports *all*
deleted objects of the source db, so merging them into the whole database could delete
unrelated items that share a uuid. The scratch-copy approach removes that risk and avoids
moving entries across the tree.

**Export algorithm:**
1. `exp.New(new IOConnectionInfo(), key(ref.Password), group.Name)` and set
   `exp.RootGroup = share.Group.CloneDeep()`. Remove `KeeShare/Reference` and every
   `KP2A/KeeShare/*` key from the root's CustomData. If `!KeepGroups`, clear the root's
   subgroups. Set `exp.RecycleBinEnabled = false` and `exp.Name = group.Name`. Copy the
   custom icons used in the subtree, and copy `db.KpDatabase.DeletedObjects` (KeePassXC parity).
2. Serialize with `new KdbxFile(exp).Save(ms, null, KdbxFormat.Default, null)`, then
   `KeeShareContainer.WrapForWrite(bytes, KindForWrite(fileStorage.GetDisplayName(ioc) /
   ioc.Path))`. The file name is used only for the extension check and is never logged.
3. Write with `fs = app.GetFileStorage(ioc, allowCache: false)` and
   `using var t = fs.OpenWriteTransaction(ioc, app.GetBooleanPreference(PreferenceKey.UseFileTransactions))`,
   then write and call `t.CommitWrite()`. There is no SaveAs.
4. Record the fingerprint.

### 2.5 UI

- **Database settings** (`pref_database.xml`): add "KeeShare groups", which opens
  `ConfigureKeeShareActivity` via intent action `kp2a.action.ConfigureKeeShareActivity`.
  Change the English title "Child databases" to "Child databases (KeeAutoExec)", following
  the maintainer's suggestion. The app settings screen gets switches for
  `keeshare_import_enabled` and `keeshare_export_enabled`.
- **ConfigureKeeShareActivity** (`LockCloseActivity`, layout `config_keeshare.xml`, row
  `keeshare_config_row.xml`) lists `KeeShareGroups.Find(App.Kp2a.CurrentDb)`. Each row
  shows the group name, a type label (Imported from / Exported to / Synchronized with /
  Inactive), and this device's location as `GetDisplayName`, "next to database: ‹rel›" or
  "Not set on this device". It also shows `LastResult`. The row's buttons are "Edit"
  (opens `EditKeeShareActivity`) and "Sync now"
  (`KeeShareScheduler.Enqueue(…, Both)`). Edits are saved with
  `SaveDb` + `ActionInContextInstanceOnOperationFinished`, the same way
  `ConfigureChildDatabasesActivity` does.
- **EditKeeShareActivity** (`LockCloseActivity`, layout `edit_keeshare.xml`) takes extras
  `EXTRA_GROUP_UUID` (hex) and the database ioc. Its fields:
  - Type spinner: Inactive / Import / Export / Synchronize.
  - Path text, i.e. the KeePassXC/desktop path, kept as is.
  - Password (masked).
  - Keep groups checkbox.
  - "File on this device" button, which opens `SelectStorageLocationActivity`. It uses
    `WritableRequirements.WriteDemanded` for exporting types and `ReadOnly` for Import,
    with `ExtraIsForSave` true for exporting types. The result is read with
    `Util.SetIoConnectionFromIntent`, followed by `KeeShareGroups.SetDeviceIoc`.
  - "Clear device file" and "Remove sharing" buttons.

  After a device file is picked for a share with an absolute `Reference.Path`, call
  `KeeShareMountMap.TryDerive(Reference.Path, KeeSharePath.Segments(fs.GetDisplayName(ioc)))`.
  On success, show a checkbox `KeeShareRememberMount`: "Also use ‹folder display name› for
  other shares under ‹desktopPrefix› on this device", checked by default. If confirmed,
  the folder IOC is the picked IOC after `parentSteps` calls to `GetParentPath`. It is
  stored with `KeeShareLocationResolver.SetMounts`.
- **ConfigureKeeShareActivity** also has a "Mount mappings on this device" section. It
  lists each `DesktopPrefix` → folder `GetDisplayName`, with a remove action. Mappings are
  only created through the derive flow above.

  Save calls `SetReference` and then `SaveDb`. The resulting save triggers an export.
- **Entry point from a group**: `group_entriesselected.xml` gets a `menu_keeshare` item
  ("KeeShare…"), visible when exactly one group is selected and the db can be written. It
  opens `EditKeeShareActivity` for that group.
- **Read-only enforcement**: `KeeShareGroups.IsReadOnlyContent(db, group)` gates the
  following. Each gate uses the same check as the existing `CanWrite` gating.
  - `GroupActivity.AddGroupEnabled`/`AddEntryEnabled`.
  - `EntryActivity`'s edit menu.
  - `EntryEditActivity` (refuses to open with a toast).
  - `GroupBaseActivity`'s action mode (delete/move/edit/paste-into) when any selected
    element, or the target group, is read-only content.

  An info line "Imported from KeeShare – read only" appears above the list in a read-only
  share group.

### 2.6 Conventions

- C# style as in surrounding files: 2-space indentation, `_camelCase` fields, GPL license
  header (copy the 2025 header from `KeeAutoExec.cs`).
- Logging: `Kp2aLog.Log("KeeShare: … " + fileStorage.GetDisplayName(ioc))`. Never log
  `ioc.Path`, passwords, `SerializeToString` output or reference XML.
  `Kp2aLog.LogUnexpectedError(e)` only for unexpected exceptions.
- Operations: subclass `OperationWithFinishHandler` and run through `OperationRunner.Instance.Run`.
  Catch `Java.Lang.InterruptedException`/`Java.IO.InterruptedIOException` without `Finish()`,
  as `SynchronizeCachedDatabase` does.
- File I/O only through `IFileStorage` (`OpenFileForRead`, `OpenWriteTransaction`,
  `GetParentPath`, `GetFilePath`, `GetDisplayName`).
- Strings: English only in `Resources/values/strings.xml`. Crowdin handles translations.
- Device id: `KeeAutoExecExt.ThisDeviceId`, set into `KeeShareScheduler.DeviceId` at app
  start (`App.OnCreate`), so business logic does not depend on the app project.

### 2.7 Error handling

| Condition | Behaviour |
|---|---|
| Undecodable reference | Group treated as unshared; logged once per load: "KeeShare: invalid reference on group ‹name›" |
| Location not set | Item `Skipped`, shown in config UI, no toast |
| File missing on import | `Failed: KeeShareFileNotFound`; db untouched |
| File missing on export | Created by the write transaction |
| Wrong password / corrupt KDBX / zip without entry | `Failed` with `KeeShareWrongPassword` / exception message; db untouched |
| Network / storage error | `Failed` with `ExceptionUtil.GetErrorMessage(e)`; other shares continue |
| Db read-only | Import in memory, `KeeShareDatabaseReadOnly` info, no save/export |
| SMB connect/login failure | `Failed` with the storage's message (host or username only, never the password); other shares continue |
| SMB file missing | `FileNotFoundException` from hardened `SmbFileStorage` → `KeeShareFileNotFound` |
| SMB rename failed (file transactions) | `CommitWrite` throws → `Failed`; fingerprint not recorded, so the next trigger retries |
| UNC path, no matching SMB credentials | `Skipped: KeeShareSmbCredentialsNeeded` |
| Offline mode, non-local share | `Skipped: KeeShareOffline` |
| `smb://` in NoNet flavor | `Skipped: KeeShareStorageUnavailable` |
| Share read while KeePassXC is mid-write (truncated zip/KDBX) | `Failed`; db untouched; retried on the next trigger |
| Global pref off | Scheduler does not enqueue the corresponding mode |
| Nested SaveDb fails | Operation finishes `false` with SaveDb's message; no export phase |

## 3. Tasks

Feature edits must stay distinct from the user's committed environment setup
(commit `42e395f9`: `AGENTS.md`, `.agents/skills/android-e2e/SKILL.md`, `docs/development.md`,
`flake.nix`, `flake.lock`, `scripts/kp2a`, `tests/e2e/run.py`, `.gitignore`, and the
`Kp2aBusinessLogic.csproj` Dropbox line). Tasks that touch those files make additive edits only.

All commands run from the repo root. `kp2a setup` must have been run once.

### Wave 1 (parallel)

**T1 — Core KeeShare library + host tests**
- Goal: implement `Kp2aKeeShare` (§2.3 first block) with xunit tests: golden KeePassXC
  reference strings (Import, Export, Synchronize, no KeepGroups, empty password, unicode
  path), round-trip, invalid input → `false`, uuid byte order, zip extract/wrap, magic
  detection, `KindForWrite`, `KeeSharePath.Choose` matrix (device ioc / mount / UNC / relative /
  NotSet precedence), `Segments`/`IsAbsolute`/`IsWindowsStyle`, `KeeShareMountMap` codec, longest-prefix
  and segment-boundary matching (`/mnt/nas` must not match `/mnt/nas2/x`), Windows case-insensitivity,
  `TryDerive` (`/mnt/nas/keeshare/team.kdbx` + `smb://host/share/keeshare/team.kdbx` → prefix
  `/mnt/nas`, 2 parent steps; mismatched file name → false), `KeeShareSmbPath.TryParseUnc` for all three
  syntaxes, `BorrowCredentials` (same host case-insensitive → credential part copied verbatim incl.
  URL-encoded `@`/`:`; different host → null), and fingerprint order-independence.
- Files: `src/Kp2aKeeShare/**`, `src/Kp2aKeeShare.Tests/**`, `src/KeePass.sln` (add both
  projects), `src/Kp2aBusinessLogic/Kp2aBusinessLogic.csproj` (add a `ProjectReference`
  only), and `scripts/kp2a` (the `test` case additionally runs
  `dotnet test src/Kp2aKeeShare.Tests/Kp2aKeeShare.Tests.csproj`).
- Consumes: nothing. Produces: §2.3 `Kp2aKeeShare` API.
- Depends: —.
- Test: `nix develop --command kp2a test` (both suites). Narrow form:
  `nix run . -- -c 'dotnet test src/Kp2aKeeShare.Tests/Kp2aKeeShare.Tests.csproj'`.

**T2 — Resources and string keys**
- Goal: add every resource the feature needs: strings for §2.3 `UiStringKey` names and the
  UI labels; layouts `config_keeshare.xml`, `keeshare_config_row.xml`, `edit_keeshare.xml`
  (ids: `keeshare_list`, `keeshare_row_name`, `keeshare_row_type`, `keeshare_row_location`,
  `keeshare_row_status`, `keeshare_row_edit`, `keeshare_row_sync`, `keeshare_type_spinner`,
  `keeshare_path`, `keeshare_password`, `keeshare_keep_groups`, `keeshare_pick_device_file`,
  `keeshare_device_file_label`, `keeshare_clear_device_file`, `keeshare_remove`,
  `keeshare_save`, `keeshare_readonly_info`, `keeshare_remember_mount`, `keeshare_mount_list`,
  plus row layout `keeshare_mount_row.xml` with `keeshare_mount_prefix`, `keeshare_mount_folder`,
  `keeshare_mount_remove`); the `menu_keeshare` item in
  `group_entriesselected.xml`; `arrays.xml` keeshare_types; the `pref_database.xml` entry
  and Child-databases title change; app-settings switches with keys
  `keeshare_import_enabled`/`keeshare_export_enabled`; the `UiStringKey` enum values.
- Files: `src/keepass2android-app/Resources/values/strings.xml`, `Resources/values/arrays.xml`,
  `Resources/layout/config_keeshare.xml`, `Resources/layout/keeshare_config_row.xml`,
  `Resources/layout/edit_keeshare.xml`, `Resources/layout/keeshare_mount_row.xml`,
  `Resources/menu/group_entriesselected.xml`,
  `Resources/xml/pref_database.xml`, the app-settings preference XML that holds sync
  settings (locate it via `pref_enable_periodic_background_sync`),
  `src/Kp2aBusinessLogic/UiStringKey.cs`, and `src/Kp2aBusinessLogic/PreferenceKey.cs`.
- Consumes: —. Produces: resource ids/strings/keys listed above.
- Depends: —.
- Test: `nix develop --command kp2a build` (resource compile).

**T3 — E2E fixtures tooling**
- Goal: `tests/e2e/keeshare/make_fixtures.py OUTDIR` uses pykeepass to generate synthetic
  files:
  - `main.kdbx` (password `main-pass`) containing a group "Team Import" with a
    KeePassXC-encoded `KeeShare/Reference` (Import, Path `team-import.kdbx`, password
    `share-pass`) and a group "Team Sync" (Synchronize, Path `team-sync.kdbx.share`,
    KeepGroups True). The reference is written into the group's `<CustomData>` via
    pykeepass's lxml tree, with the encoding byte-for-byte as in §2.2.
  - `team-import.kdbx` with entry "Imported Entry".
  - `team-sync.kdbx.share` as a zip with `container.share.kdbx`, containing entry
    "Remote Sync Entry".

  The tooling also provides `verify_share.py PATH PASSWORD EXPECTED_TITLE...`, which
  asserts that the titles are present in the share and exits nonzero otherwise. Add
  `pykeepass` to the flake's Python
  (`p.python3` → `(p.python3.withPackages (ps: [ ps.pykeepass ]))`). This is an additive
  edit to `flake.nix`; `flake.lock` stays unchanged.
- Files: `tests/e2e/keeshare/make_fixtures.py`, `tests/e2e/keeshare/verify_share.py`, `flake.nix`.
- Consumes: §2.2 format. Produces: fixture files and verifier CLI.
- Depends: —.
- Test: `nix develop --command bash -c 'd=$(mktemp -d) && python3 tests/e2e/keeshare/make_fixtures.py $d && python3 tests/e2e/keeshare/verify_share.py $d/team-sync.kdbx.share share-pass "Remote Sync Entry"'`.

**T9 — SmbFileStorage hardening**
- Goal: the §2.3 `SmbFileStorage` hardening. Map not-found statuses to
  `FileNotFoundException`, check the rename status (throw, then delete the temp file on a
  best-effort basis), close file handles, and keep credentials out of exception messages.
  No public API change. Note: `SynchronizeCachedDatabase` already treats
  `FileNotFoundException` as "remote missing → restore from cache", which is the intended
  semantics for SMB databases too.
- Files: `src/Kp2aBusinessLogic/Io/SmbFileStorage.cs`.
- Consumes: —. Produces: hardened SMB storage.
- Depends: —.
- Test: `nix develop --command kp2a build`. The user skipped SMB e2e, and SMBLibrary sits
  inside the Android assembly with no host harness, so verification is the build plus
  review of each status check against the SMBLibrary `NTStatus` values.

### Wave 2

**T4 — Business-logic KeeShare engine**
- Goal: implement the §2.3 `Kp2aBusinessLogic/KeeShare` API with the §2.4 import/export
  algorithms, `KeeShareSyncOperation` and `KeeShareScheduler`, following the §2.7 error
  handling and the §2.6 logging rules.
- Files: `src/Kp2aBusinessLogic/KeeShare/KeeShareGroups.cs`, `KeeShareLocationResolver.cs`,
  `KeeShareImporter.cs`, `KeeShareExporter.cs`, `KeeShareSyncOperation.cs`, `KeeShareScheduler.cs`,
  and `src/Kp2aBusinessLogic/database/edit/SaveDB.cs` (`SkipKeeShareExport` + Enqueue hook).
- Consumes: T1 API, T2 `UiStringKey`/`PreferenceKey`, T9 (`FileNotFoundException` from SMB).
  Produces: §2.3 business API, `SaveDb.SkipKeeShareExport`.
- Depends: T1, T2, T9.
- Test: `nix develop --command kp2a build` + `nix develop --command kp2a test`. KeePassLib is
  `net9.0-android` with native Argon2, so merge and export behaviour is not host-testable
  and is proven by the E2E journey.

### Wave 3 (parallel)

**T5 — Trigger integration**
- Goal: wire the §2.4 trigger table. In `SyncUtil`, enqueue `Both` from the sync-finished
  handler on success. In `SelectCurrentDbActivity`, enqueue `Import` for an opened db when
  no pending background sync was queued for its ioc. In `App.OnCreate`, set
  `KeeShareScheduler.DeviceId` and `KeeShareScheduler.IsOffline = () => App.Kp2a.OfflineMode`.
  When the user switches back online (the `menu_work_online` handler goes through
  `SyncUtil`), the resulting sync's `Both` trigger picks up skipped shares.
- Files: `src/keepass2android-app/SyncUtil.cs`, `src/keepass2android-app/SelectCurrentDbActivity.cs`,
  `src/keepass2android-app/app/App.cs`.
- Consumes: `KeeShareScheduler`. Produces: automatic import/export.
- Depends: T4.
- Test: `nix develop --command kp2a build`.

**T6 — Configuration UI**
- Goal: `ConfigureKeeShareActivity` (including the mount-mappings section) and
  `EditKeeShareActivity` (including the derive-mount checkbox flow) per §2.5. Register the
  intent action like `ConfigureChildDatabasesActivity`, and add the `menu_keeshare`
  handling in the action mode.
- Files: `src/keepass2android-app/ConfigureKeeShareActivity.cs`,
  `src/keepass2android-app/EditKeeShareActivity.cs`, and `src/keepass2android-app/GroupBaseActivity.cs`
  (the `menu_keeshare` case, its visibility, and the read-only gating of
  delete/move/edit/paste-into via `KeeShareGroups.BlocksModification`).
- Consumes: T2 resources, T4 API. Produces: config UI.
- Depends: T2, T4.
- Test: `nix develop --command kp2a build`.

**T7 — Read-only import groups**
- Goal: the §2.5 read-only enforcement in group/entry screens and the info line. T6 owns
  the action-mode gating in `GroupBaseActivity` (delete, move, edit, paste-into).
- Files: `src/keepass2android-app/GroupActivity.cs`, `src/keepass2android-app/EntryActivity.cs`,
  `src/keepass2android-app/EntryEditActivity.cs`.
- Consumes: `KeeShareGroups.IsReadOnlyContent`. Produces: read-only UI.
- Depends: T2, T4.
- Test: `nix develop --command kp2a build`.

### Wave 4

**T8 — E2E journey script**
- Goal: implement §5 as `tests/e2e/keeshare_journey.py`. It reuses the uiautomator dump,
  find and tap pattern from `tests/e2e/run.py` (copying the helpers, without editing
  `run.py`). It uses only `adb -s "$ANDROID_SERIAL"`, and writes artifacts (screens, XML,
  pulled files) to `$KP2A_E2E_ARTIFACTS`. Fixtures are pushed into the debuggable app's
  private files dir via `run-as "$KP2A_E2E_PACKAGE"`. The database is opened from
  KP2A's internal-storage browser, so relative share paths resolve through
  `BuiltInFileStorage.GetParentPath`.
- Files: `tests/e2e/keeshare_journey.py`.
- Consumes: T3 fixtures/verifier, the built APK. Produces: e2e evidence.
- Depends: T3, T5, T6, T7.
- Test: `nix run . -- -c 'kp2a build && kp2a e2e -- python3 tests/e2e/keeshare_journey.py'`.

## 4. Test and verification

| Check | Command | Proves |
|---|---|---|
| Unit (host) | `nix develop --command kp2a test` | Autofill + Kp2aKeeShare suites (codec, containers, path policy, fingerprint) |
| Build / compile / type check | `nix develop --command kp2a build` | All C# compiles (C# is the type check), resources link, signed Debug APK produced |
| Lint / format | `git diff --check` and visual style match. The repo has no lint target; `setup_format_and_license.ps1` (license headers) is Windows-only and is not required | No whitespace errors; license headers present on new `.cs` files |
| Smoke e2e | `nix develop --command kp2a e2e` | App still starts and opens the creation form |
| Feature e2e | `nix run . -- -c 'kp2a build && kp2a e2e -- python3 tests/e2e/keeshare_journey.py'` | §5 journey |
| SMB coverage | Host unit tests for UNC parsing, mount maps, deriving a mapping and credential borrowing (T1), plus the build (T9). The user explicitly skipped Samba e2e | AC 10, except live SMB I/O |
| Secret-logging audit | `git diff main -- src \| grep -nE 'Log\(.*(\.Path\|Password\|SerializeToString)'` returns nothing | AC 8 |

Every e2e run uses a new isolated emulator through `kp2a e2e`, as `AGENTS.md` and
`.agents/skills/android-e2e/SKILL.md` require. Never use an existing emulator or device.
Report the APK tested, the results and `.dev/e2e/run-*/` artifact path.

## 5. E2E journey

Run: `nix run . -- -c 'kp2a build && kp2a e2e -- python3 tests/e2e/keeshare_journey.py'`.
Use synthetic data only. Each step asserts visible UI (uiautomator XML) or pulled-file
content and saves a screenshot to `$KP2A_E2E_ARTIFACTS`.

1. **Prepare.** Generate fixtures with `make_fixtures.py`. Push `main.kdbx`,
   `team-import.kdbx` and `team-sync.kdbx.share` to the app files dir (`run-as`).
   → The files exist (`run-as … ls`).
2. **Open the database.** Launch the app, open `main.kdbx` from internal storage, and enter
   `main-pass`. → The group list shows "Team Import" and "Team Sync".
3. **Automatic import via relative paths.** Wait for the background operation and open
   "Team Import". → "Imported Entry" is listed, along with the read-only info line.
4. **Read-only enforcement.** In "Team Import", the add (FAB) button is absent, and
   long-pressing "Imported Entry" offers no Delete or Move.
5. **Synchronize import from a zip container.** Open "Team Sync". → "Remote Sync Entry" is
   listed and the add button is present.
6. **Export on save.** In "Team Sync", add an entry "Local Sync Entry" and save. Wait for
   the background operation, then pull `team-sync.kdbx.share`.
   → `verify_share.py team-sync.kdbx.share share-pass "Remote Sync Entry" "Local Sync Entry"`
   passes, and the file is a zip containing `container.share.kdbx`.
7. **Configuration screen.** Open Database settings → "KeeShare groups". → Two rows appear,
   "Imported from" and "Synchronized with", each with location "next to database" and no
   error.
8. **Create a share in KP2A.** Long-press a regular group "Personal", choose "KeeShare…",
   set Type Export, Path `personal-export.kdbx` and password `exp-pass`, then save.
   → After the background save, `personal-export.kdbx` exists in the files dir.
   `verify_share.py … exp-pass <Personal entry title>` passes, and the export root has no
   `KeeShare/Reference` CustomData (checked by the verifier with `--no-reference`).
9. **Per-device location is honoured, with an error path.** Edit "Team Import" and use
   "File on this device" to pick a non-existent or garbage file (a pushed
   `bad.kdbx` with random bytes). Trigger "Sync now".
   → An error message names "Team Import". Its row shows a failed status, and "Imported
   Entry" is still present (the db was not modified).
10. **No secrets in logs.** Grep `logcat.txt` for `main-pass`, `share-pass`, `exp-pass`
    and the app files-dir absolute path inside
    "KeeShare:" lines. → No matches.

SMB is deliberately not part of this journey (user decision). Mount mapping and UNC
resolution are covered by host unit tests, and `SmbFileStorage` hardening by build and
review.

Pass criteria: every step's assertion holds and the script exits 0. On failure, the script
exits nonzero and names the step that failed.
