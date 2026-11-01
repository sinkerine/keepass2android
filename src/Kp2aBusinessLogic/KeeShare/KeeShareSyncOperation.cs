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

using KeePass.Util;
using KeePassLib;
using KeePassLib.Keys;
using KeePassLib.Serialization;

namespace keepass2android.KeeShare;

[Flags] public enum KeeShareSyncMode { Import = 1, Export = 2, Both = 3 }
public enum KeeShareOutcome { Unchanged, Imported, Exported, ImportedAndExported, Skipped, Failed }
public sealed record KeeShareItemResult(PwUuid GroupUuid, string GroupName, KeeShareOutcome Outcome, string? Message);

public class KeeShareSyncOperation : OperationWithFinishHandler
{
  private readonly IKp2aApp _app;
  private readonly Database _db;
  private KeeShareSyncMode _mode;
  private readonly object _modeLock = new();
  private bool _started;
  private readonly List<KeeShareItemResult> _results = new();
  public IReadOnlyList<KeeShareItemResult> Results => _results.AsReadOnly();

  public KeeShareSyncOperation(IKp2aApp app, Database db, KeeShareSyncMode mode,
    OnOperationFinishedHandler operationFinishedHandler) : base(app, operationFinishedHandler)
  {
    _app = app;
    _db = db;
    _mode = mode;
  }

  internal bool AddMode(KeeShareSyncMode mode)
  {
    lock (_modeLock)
    {
      if (_started) return false;
      _mode |= mode;
      return true;
    }
  }

  public override void Run()
  {
    lock (_modeLock) _started = true;
    KeeShareScheduler.Started(_db, this);
    try
    {
      var importEnabled = _app.GetBooleanPreference(PreferenceKey.keeshare_import_enabled);
      var exportEnabled = _app.GetBooleanPreference(PreferenceKey.keeshare_export_enabled);
      if (!importEnabled) _mode &= ~KeeShareSyncMode.Import;
      if (!exportEnabled) _mode &= ~KeeShareSyncMode.Export;
      StatusLogger.UpdateMessage(_mode.HasFlag(KeeShareSyncMode.Import)
        ? UiStringKey.KeeShareImporting : UiStringKey.KeeShareExporting);
      var shares = KeeShareGroups.Find(_db);
      var locations = new Dictionary<PwUuid, IOConnectionInfo>();
      var changed = KeeShareScheduler.NeedsSave(_db);
      foreach (var initialShare in shares)
      {
        // Importing an ancestor can replace descendants, so always use the live group.
        var share = KeeShareGroups.Find(_db).FirstOrDefault(candidate => candidate.Group.Uuid.Equals(initialShare.Group.Uuid));
        if (share == null) continue;
        var importing = share.Reference.IsImporting && (_mode.HasFlag(KeeShareSyncMode.Import) ||
          (_mode.HasFlag(KeeShareSyncMode.Export) && share.Reference.IsExporting));
        var exporting = share.Reference.IsExporting && _mode.HasFlag(KeeShareSyncMode.Export);
        if (!importing && !exporting) continue;
        if (importing && !importEnabled)
        {
          // Synchronize cannot safely export without its prerequisite import.
          SetResult(share, KeeShareOutcome.Skipped, _app.GetResourceString(UiStringKey.KeeShareImportRequired));
          continue;
        }
        var ioc = KeeShareLocationResolver.Resolve(_app, share, KeeShareScheduler.DeviceId, out var problem);
        if (ioc == null)
        {
          SetResult(share, KeeShareOutcome.Skipped, _app.GetResourceString(LocationMessage(problem)));
          continue;
        }
        locations[share.Group.Uuid] = ioc;
        SetResult(share, KeeShareOutcome.Unchanged);
        if (!importing) continue;
        try
        {
          StatusLogger.UpdateMessage(UiStringKey.KeeShareImporting);
          var watcher = new BackgroundDatabaseModificationLocker(_app);
          watcher.BeforeModifyDatabases();
          try
          {
            if (KeeShareImporter.Import(_app, share, ioc, StatusLogger))
            {
              changed = true;
              KeeShareScheduler.RequireSave(_db);
              // Replacing the subtree also replaces object identities. Rebuild the indexes
              // before releasing the modification lock, even if the subsequent save fails.
              _db.UpdateGlobals();
              _app.UiThreadHandler.Post(() => _app.MarkAllGroupsAsDirty());
              SetResult(share, KeeShareOutcome.Imported, _app.GetResourceString(UiStringKey.KeeShareImportedChanges));
            }
          }
          finally { watcher.AfterModifyDatabases(); }
        }
        catch (Java.Lang.InterruptedException) { throw; }
        catch (Java.IO.InterruptedIOException) { throw; }
        catch (Exception exception) { Fail(share, ioc, exception); }
      }
      if (changed)
      {
        if (!_db.CanWrite)
        {
          foreach (var result in _results.Where(result => result.Outcome != KeeShareOutcome.Failed &&
                     result.Outcome != KeeShareOutcome.Skipped).ToArray())
            ReplaceResult(result with { Message = _app.GetResourceString(UiStringKey.KeeShareDatabaseReadOnly) });
          Complete();
          return;
        }
        var save = new SaveDb(_app, _db, new ActionOnOperationFinished(_app, (success, message, context) =>
        {
          // SaveDb can merge the parent database too. Refresh those replacements under
          // the same lock on either outcome, before completion can notify UI consumers.
          var watcher = new BackgroundDatabaseModificationLocker(_app);
          watcher.BeforeModifyDatabases();
          try
          {
            _db.UpdateGlobals();
            _app.UiThreadHandler.Post(() => _app.MarkAllGroupsAsDirty());
          }
          finally { watcher.AfterModifyDatabases(); }
          if (!success)
          {
            // SaveDb has already reported its storage error; never export unsaved imported changes.
            var safeMessage = SafeMessage(message, locations) ?? _app.GetResourceString(UiStringKey.KeeShareFailed);
            foreach (var result in _results.Where(result => result.Outcome == KeeShareOutcome.Imported).ToArray())
              ReplaceResult(result with { Outcome = KeeShareOutcome.Failed, Message = safeMessage });
            KeeShareScheduler.RecordResults(_db, _results);
            Finish(false, safeMessage);
            return;
          }
          KeeShareScheduler.Saved(_db);
          ExportAndComplete(locations, true);
        }), new BackgroundDatabaseModificationLocker(_app))
        {
          SkipKeeShareExport = true,
          DoNotSetStatusLoggerMessage = true
        };
        save.SetStatusLogger(StatusLogger);
        save.Run();
        return;
      }
      ExportAndComplete(locations, false);
    }
    catch (Java.Lang.InterruptedException) { }
    catch (Java.IO.InterruptedIOException) { }
    catch (Exception exception)
    {
      Kp2aLog.LogUnexpectedError(new Exception("KeeShare operation failed (" + exception.GetType().Name + ")."));
      Finish(false, _app.GetResourceString(UiStringKey.KeeShareFailed));
    }
  }

  private void ExportAndComplete(Dictionary<PwUuid, IOConnectionInfo> locations, bool importedChanges)
  {
    try
    {
      if (_db.CanWrite && _app.GetBooleanPreference(PreferenceKey.keeshare_export_enabled) &&
          (_mode.HasFlag(KeeShareSyncMode.Export) || importedChanges))
      {
        StatusLogger.UpdateMessage(UiStringKey.KeeShareExporting);
        foreach (var share in KeeShareGroups.Find(_db).Where(share => share.Reference.IsExporting))
        {
          var previous = _results.FirstOrDefault(result => result.GroupUuid.Equals(share.Group.Uuid));
          if (previous?.Outcome is KeeShareOutcome.Failed or KeeShareOutcome.Skipped) continue;
          // A share newly discovered during import still needs a prerequisite import before export.
          if (share.Reference.IsImporting && !locations.ContainsKey(share.Group.Uuid)) continue;
          var ioc = KeeShareLocationResolver.Resolve(_app, share, KeeShareScheduler.DeviceId, out var problem);
          if (ioc == null)
          {
            SetResult(share, KeeShareOutcome.Skipped, _app.GetResourceString(LocationMessage(problem)));
            continue;
          }
          try
          {
            var watcher = new BackgroundDatabaseModificationLocker(_app);
            watcher.BeforeModifyDatabases();
            try
            {
              if (KeeShareScheduler.ExportUnchanged(share, ioc, KeeShareImporter.Fingerprint(share.Group))) continue;
              KeeShareExporter.Export(_app, share, ioc, StatusLogger);
              SetResult(share, previous?.Outcome == KeeShareOutcome.Imported
                ? KeeShareOutcome.ImportedAndExported : KeeShareOutcome.Exported, previous?.Message);
            }
            finally { watcher.AfterModifyDatabases(); }
          }
          catch (Java.Lang.InterruptedException) { throw; }
          catch (Java.IO.InterruptedIOException) { throw; }
          catch (Exception exception) { Fail(share, ioc, exception); }
        }
      }
      Complete();
    }
    catch (Java.Lang.InterruptedException) { }
    catch (Java.IO.InterruptedIOException) { }
    catch (Exception exception)
    {
      Kp2aLog.LogUnexpectedError(new Exception("KeeShare export failed (" + exception.GetType().Name + ")."));
      Finish(false, _app.GetResourceString(UiStringKey.KeeShareFailed));
    }
  }

  private static UiStringKey LocationMessage(KeeShareLocationProblem problem) => problem switch
  {
    KeeShareLocationProblem.SmbCredentialsNeeded => UiStringKey.KeeShareSmbCredentialsNeeded,
    KeeShareLocationProblem.StorageUnavailable => UiStringKey.KeeShareStorageUnavailable,
    KeeShareLocationProblem.Offline => UiStringKey.KeeShareOffline,
    _ => UiStringKey.KeeShareLocationNotSet
  };

  private void Fail(KeeShareGroup share, IOConnectionInfo ioc, Exception exception)
  {
    var message = exception switch
    {
      NoFileStorageFoundException => _app.GetResourceString(UiStringKey.KeeShareStorageUnavailable),
      FileNotFoundException => _app.GetResourceString(UiStringKey.KeeShareFileNotFound),
      InvalidCompositeKeyException => _app.GetResourceString(UiStringKey.KeeShareWrongPassword),
      _ => Redact(ExceptionUtil.GetErrorMessage(exception), share, ioc)
    };
    if (exception is not NoFileStorageFoundException && exception is not IOException && exception is not InvalidCompositeKeyException &&
        exception is not KeeShareFormatException && exception is not System.Net.WebException &&
        exception is not Java.IO.IOException && exception is not UnauthorizedAccessException)
      Kp2aLog.LogUnexpectedError(new Exception("KeeShare failed (" + exception.GetType().Name + ")."));
    SetResult(share, KeeShareOutcome.Failed, message);
  }

  private string Redact(string message, KeeShareGroup share, IOConnectionInfo ioc)
  {
    // Providers sometimes embed raw paths in exceptions. Only display names may reach the UI.
    string display;
    try { display = _app.GetFileStorage(ioc, allowCache: false).GetDisplayName(ioc); }
    catch (NoFileStorageFoundException) { return _app.GetResourceString(UiStringKey.KeeShareStorageUnavailable); }
    foreach (var secret in new[] { IOConnectionInfo.SerializeToString(ioc), ioc.Path,
               share.Reference.Path, ioc.Password, share.Reference.Password })
      if (!string.IsNullOrEmpty(secret))
        message = message.Replace(secret, secret == ioc.Path ? display : "…", StringComparison.Ordinal);
    // A provider may report only the credential part of an SMB URI.
    var userInfo = System.Text.RegularExpressions.Regex.Match(ioc.Path, @"^[a-zA-Z][a-zA-Z0-9+.-]*://([^/]*@)");
    if (userInfo.Success)
    {
      var credentials = userInfo.Groups[1].Value.TrimEnd('@').Split(':', 2);
      foreach (var credential in credentials.Skip(1))
        if (!string.IsNullOrEmpty(credential))
        {
          message = message.Replace(credential, "…", StringComparison.Ordinal);
          var decoded = Uri.UnescapeDataString(credential);
          if (decoded.Length != 0) message = message.Replace(decoded, "…", StringComparison.Ordinal);
        }
    }
    return message;
  }

  private string? SafeMessage(string? message, Dictionary<PwUuid, IOConnectionInfo> locations)
  {
    if (message == null) return null;
    foreach (var share in KeeShareGroups.Find(_db))
      if (locations.TryGetValue(share.Group.Uuid, out var ioc)) message = Redact(message, share, ioc);
    // The parent database can also contain credentials.
    return string.IsNullOrEmpty(_db.Ioc.Path) ? message :
      message.Replace(_db.Ioc.Path, _app.GetFileStorage(_db.Ioc).GetDisplayName(_db.Ioc), StringComparison.Ordinal);
  }

  private void SetResult(KeeShareGroup share, KeeShareOutcome outcome, string? message = null) =>
    ReplaceResult(new KeeShareItemResult(share.Group.Uuid, share.Group.Name, outcome, message));

  private void ReplaceResult(KeeShareItemResult result)
  {
    var index = _results.FindIndex(previous => previous.GroupUuid.Equals(result.GroupUuid));
    if (index < 0) _results.Add(result);
    else _results[index] = result;
  }

  private void Complete()
  {
    KeeShareScheduler.RecordResults(_db, _results);
    var failed = _results.Any(result => result.Outcome == KeeShareOutcome.Failed);
    var messages = _results.Where(result => result.Outcome != KeeShareOutcome.Unchanged &&
      result.Outcome != KeeShareOutcome.Skipped && !string.IsNullOrEmpty(result.Message))
      .Select(result => result.GroupName + ": " + result.Message);
    var message = string.Join("\n", messages);
    Finish(!failed, message.Length == 0 ? null : "KeeShare: " + message);
  }
}
