// This file is part of Keepass2Android, Copyright 2025 Philipp Crocoll.
//
//   Keepass2Android is free software: you can redistribute it and/or modify
//   it under the terms of the GNU General Public License as published by
//   the Free Software Foundation, either version 3 of the License, or
//   (at your option) any later version.
//
//   Keepass2Android is distributed in the hope that it will be useful,
//   but WITHOUT ANY WARRANTY; without even the implied warranty of
//   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//   GNU General Public License for more details.
//
//   You should have received a copy of the GNU General Public License
//   along with Keepass2Android.  If not, see <http://www.gnu.org/licenses/>.

using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using KeePassLib;
using KeePassLib.Serialization;

namespace keepass2android.KeeShare;

public static class KeeShareScheduler
{
  private sealed class DatabaseState
  {
    public KeeShareSyncOperation? Pending;
    public bool NeedsSave;
    public readonly Dictionary<string, KeeShareItemResult> Results = new();
    public readonly Dictionary<string, (string Hash, string Fingerprint)> Imports = new();
    public readonly Dictionary<string, string> Exports = new();
  }

  // Database lifetimes do not keep closed databases (or their credentials) alive.
  private static readonly ConditionalWeakTable<PwDatabase, DatabaseState> _states = new();
  private static readonly object _stateLock = new();
  private static readonly object _enqueueLock = new();
  public static string DeviceId { get; set; } = "";
  public static Func<bool> IsOffline { get; set; } = () => false;

  public static void Enqueue(IKp2aApp app, Database db, KeeShareSyncMode mode)
  {
    lock (_enqueueLock) EnqueueCore(app, db, mode);
  }

  private static void EnqueueCore(IKp2aApp app, Database db, KeeShareSyncMode mode)
  {
    if (!app.GetBooleanPreference(PreferenceKey.keeshare_import_enabled)) mode &= ~KeeShareSyncMode.Import;
    if (!app.GetBooleanPreference(PreferenceKey.keeshare_export_enabled)) mode &= ~KeeShareSyncMode.Export;
    if (mode == 0 || !KeeShareGroups.Find(db).Any(share =>
          (mode.HasFlag(KeeShareSyncMode.Import) && share.Reference.IsImporting) ||
          (mode.HasFlag(KeeShareSyncMode.Export) && share.Reference.IsExporting))) return;

    KeeShareSyncOperation? pending;
    lock (_stateLock) pending = _states.GetOrCreateValue(db.KpDatabase).Pending;
    // CancelAll drops queued operations without callbacks. Recheck membership after the update
    // so cancellation/dequeue during coalescing cannot strand this request in a stale operation.
    if (pending != null && OperationRunner.Instance.IsQueued(pending) && pending.AddMode(mode) &&
        OperationRunner.Instance.IsQueued(pending)) return;

    KeeShareSyncOperation operation;
    lock (_stateLock)
    {
      var state = _states.GetOrCreateValue(db.KpDatabase);
      operation = new KeeShareSyncOperation(app, db, mode, new ActionOnOperationFinished(app,
        (success, message, context) =>
        {
          if (!string.IsNullOrEmpty(message))
            app.UiThreadHandler.Post(() => app.ShowMessage(context, message,
              success ? MessageSeverity.Info : MessageSeverity.Error));
        }));
      state.Pending = operation;
    }
    // Do not hold the cache lock while taking OperationRunner's queue lock.
    OperationRunner.Instance.Run(app, operation);
  }

  internal static void Started(Database db, KeeShareSyncOperation operation)
  {
    lock (_stateLock)
    {
      var state = _states.GetOrCreateValue(db.KpDatabase);
      if (ReferenceEquals(state.Pending, operation)) state.Pending = null;
    }
  }

  internal static bool NeedsSave(Database db)
  {
    lock (_stateLock) return _states.GetOrCreateValue(db.KpDatabase).NeedsSave;
  }

  internal static void RequireSave(Database db)
  {
    lock (_stateLock) _states.GetOrCreateValue(db.KpDatabase).NeedsSave = true;
  }

  internal static void Saved(Database db)
  {
    lock (_stateLock) _states.GetOrCreateValue(db.KpDatabase).NeedsSave = false;
  }

  public static KeeShareItemResult? LastResult(Database db, PwUuid groupUuid)
  {
    lock (_stateLock)
      return _states.GetOrCreateValue(db.KpDatabase).Results.GetValueOrDefault(groupUuid.ToHexString());
  }

  internal static void RecordResults(Database db, IEnumerable<KeeShareItemResult> results)
  {
    lock (_stateLock)
      foreach (var result in results)
        _states.GetOrCreateValue(db.KpDatabase).Results[result.GroupUuid.ToHexString()] = result;
  }

  private static string CacheKey(KeeShareGroup share, IOConnectionInfo ioc)
  {
    // Include configuration so a new file, password, or export policy cannot reuse stale state.
    var configuration = IOConnectionInfo.SerializeToString(share.Database.Ioc) + "\n" +
      IOConnectionInfo.SerializeToString(ioc) + "\n" + KeeShareReferenceCodec.Encode(share.Reference);
    return share.Group.Uuid.ToHexString() + ":" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(configuration)));
  }

  internal static bool ImportUnchanged(KeeShareGroup share, IOConnectionInfo ioc, string hash, string fingerprint)
  {
    lock (_stateLock)
      return _states.GetOrCreateValue(share.Database.KpDatabase).Imports.TryGetValue(CacheKey(share, ioc), out var seen) &&
        seen.Hash == hash && seen.Fingerprint == fingerprint;
  }

  internal static void RecordImport(KeeShareGroup share, IOConnectionInfo ioc, string hash, string fingerprint)
  {
    lock (_stateLock)
      _states.GetOrCreateValue(share.Database.KpDatabase).Imports[CacheKey(share, ioc)] = (hash, fingerprint);
  }

  internal static bool ExportUnchanged(KeeShareGroup share, IOConnectionInfo ioc, string fingerprint)
  {
    lock (_stateLock)
      return _states.GetOrCreateValue(share.Database.KpDatabase).Exports.GetValueOrDefault(CacheKey(share, ioc)) == fingerprint;
  }

  internal static void RecordExport(KeeShareGroup share, IOConnectionInfo ioc, string fingerprint)
  {
    // Import observations never count as a committed export; first eligible export always writes.
    lock (_stateLock)
      _states.GetOrCreateValue(share.Database.KpDatabase).Exports[CacheKey(share, ioc)] = fingerprint;
  }
}
