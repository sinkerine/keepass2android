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

using System;
using System.Linq;
using Android.App;
using Android.Content;
using Android.Content.PM;
using Android.OS;
using Android.Views;
using Android.Widget;
using keepass2android.KeeShare;
using KeePassLib.Serialization;

namespace keepass2android
{
  [Activity(Label = "@string/keeshare_groups", Theme = "@style/Kp2aTheme_BlueActionBar", ConfigurationChanges = ConfigChanges.Orientation | ConfigChanges.Keyboard | ConfigChanges.KeyboardHidden, Exported = true)]
  [IntentFilter(new[] { "kp2a.action.ConfigureKeeShareActivity" }, Categories = new[] { Intent.CategoryDefault })]
  public class ConfigureKeeShareActivity : LockCloseActivity
  {
    private Database _database;
    private BroadcastReceiver _updates;
    private readonly Handler _refreshHandler = new Handler(Looper.MainLooper);
    private Action _refresh;
    private string _lastResults;

    protected override void OnCreate(Bundle savedInstanceState)
    {
      base.OnCreate(savedInstanceState);
      _database = App.Kp2a.CurrentDb;
      if (_database == null) { Finish(); return; }
      SetContentView(Resource.Layout.config_keeshare);
      _updates = new UpdateReceiver(this);
      AndroidX.Core.Content.ContextCompat.RegisterReceiver(this, _updates,
        new IntentFilter(Intents.DataUpdated), (int)ReceiverFlags.NotExported);
      Update();
    }

    protected override void OnResume()
    {
      base.OnResume();
      if (_database != null)
      {
        Update();
        // Scheduler results can change without database contents changing (e.g. export or skip).
        _refresh = () =>
        {
          if (IsFinishing) return;
          var results = string.Join("\n", KeeShareGroups.Find(_database).Select(share =>
            KeeShareScheduler.LastResult(_database, share.Group.Uuid)?.ToString()));
          if (results != _lastResults) { _lastResults = results; Update(); }
          _refreshHandler.PostDelayed(_refresh, 1000);
        };
        _refreshHandler.PostDelayed(_refresh, 1000);
      }
    }

    protected override void OnPause()
    {
      _refreshHandler.RemoveCallbacksAndMessages(null);
      base.OnPause();
    }

    protected override void OnDestroy()
    {
      if (_updates != null) UnregisterReceiver(_updates);
      base.OnDestroy();
    }

    private sealed class UpdateReceiver : BroadcastReceiver
    {
      private readonly ConfigureKeeShareActivity _activity;
      public UpdateReceiver(ConfigureKeeShareActivity activity) { _activity = activity; }
      public override void OnReceive(Context context, Intent intent) { _activity.Update(); }
    }

    private void Update()
    {
      if (IsFinishing || _database?.KpDatabase?.RootGroup == null) return;
      FindViewById<ListView>(Resource.Id.keeshare_list).Adapter = new RowsAdapter(
        KeeShareGroups.Find(_database).OrderBy(s => s.Group.Name).Select(share =>
        {
          var row = LayoutInflater.Inflate(Resource.Layout.keeshare_config_row, null);
          row.FindViewById<TextView>(Resource.Id.keeshare_row_name).Text = share.Group.Name;
          row.FindViewById<TextView>(Resource.Id.keeshare_row_type).SetText(share.Reference.Type switch
          {
            KeeShareType.Import => Resource.String.keeshare_imported_from,
            KeeShareType.Export => Resource.String.keeshare_exported_to,
            KeeShareType.Synchronize => Resource.String.keeshare_synchronized_with,
            _ => Resource.String.keeshare_type_inactive
          });
          row.FindViewById<TextView>(Resource.Id.keeshare_row_location).Text = LocationLabel(share);
          var result = KeeShareScheduler.LastResult(_database, share.Group.Uuid);
          row.FindViewById<TextView>(Resource.Id.keeshare_row_status).Text = ResultLabel(result);
          var edit = row.FindViewById<Button>(Resource.Id.keeshare_row_edit);
          edit.Enabled = EditKeeShareActivity.CanConfigure(_database, share.Group);
          edit.Click += (sender, args) => EditKeeShareActivity.Launch(this, _database, share.Group);
          row.FindViewById<Button>(Resource.Id.keeshare_row_sync).Click += (sender, args) =>
            KeeShareScheduler.Enqueue(App.Kp2a, _database, KeeShareSyncMode.Both);
          return row;
        }).ToArray());
      FindViewById<ListView>(Resource.Id.keeshare_mount_list).Adapter = new RowsAdapter(
        KeeShareLocationResolver.GetMounts(_database, KeeAutoExecExt.ThisDeviceId).Mounts.Select(mount =>
        {
          var row = LayoutInflater.Inflate(Resource.Layout.keeshare_mount_row, null);
          row.FindViewById<TextView>(Resource.Id.keeshare_mount_prefix).Text = mount.DesktopPrefix;
          row.FindViewById<TextView>(Resource.Id.keeshare_mount_folder).Text = DisplayName(mount.SerializedFolderIoc);
          var remove = row.FindViewById<Button>(Resource.Id.keeshare_mount_remove);
          remove.Enabled = _database.CanWrite;
          remove.Click += (sender, args) =>
          {
            if (!_database.CanWrite) return;
            var locker = new BackgroundDatabaseModificationLocker(App.Kp2a);
            locker.BeforeModifyDatabases();
            try
            {
              KeeShareLocationResolver.SetMounts(_database, KeeAutoExecExt.ThisDeviceId,
                KeeShareLocationResolver.GetMounts(_database, KeeAutoExecExt.ThisDeviceId).Without(mount.DesktopPrefix));
            }
            finally { locker.AfterModifyDatabases(); }
            new BlockingOperationStarter(App.Kp2a, new SaveDb(App.Kp2a, _database,
              new ActionInContextInstanceOnOperationFinished(ContextInstanceId, App.Kp2a, (success, message, context) =>
              {
                if (!string.IsNullOrEmpty(message)) App.Kp2a.ShowMessage(context, message, MessageSeverity.Error);
                (context as ConfigureKeeShareActivity)?.Update();
              }))).Run();
          };
          return row;
        }).ToArray());
    }

    private string DisplayName(string serializedIoc)
    {
      try
      {
        var ioc = IOConnectionInfo.UnserializeFromString(serializedIoc);
        return App.Kp2a.GetFileStorage(ioc).GetDisplayName(ioc);
      }
      catch (Exception) { return GetString(Resource.String.KeeShareStorageUnavailable); }
    }

    private string LocationLabel(KeeShareGroup share)
    {
      var choice = KeeSharePath.Choose(share.Group.CustomData.Get(KeeSharePath.DeviceIocKey(KeeAutoExecExt.ThisDeviceId)),
        share.Reference.Path, KeeShareLocationResolver.GetMounts(_database, KeeAutoExecExt.ThisDeviceId));
      if (choice is KeeShareLocation.DeviceIoc device) return DisplayName(device.SerializedIoc);
      if (choice is KeeShareLocation.RelativeToDatabase)
        return GetString(Resource.String.keeshare_next_to_database, share.Reference.Path);
      var ioc = KeeShareLocationResolver.Resolve(App.Kp2a, share, KeeAutoExecExt.ThisDeviceId, out var problem);
      if (ioc != null) return DisplayName(IOConnectionInfo.SerializeToString(ioc));
      return GetString(problem switch
      {
        KeeShareLocationProblem.SmbCredentialsNeeded => Resource.String.KeeShareSmbCredentialsNeeded,
        KeeShareLocationProblem.StorageUnavailable => Resource.String.KeeShareStorageUnavailable,
        KeeShareLocationProblem.Offline => Resource.String.KeeShareOffline,
        _ => Resource.String.KeeShareLocationNotSet
      });
    }

    private string ResultLabel(KeeShareItemResult result)
    {
      if (result == null) return "";
      if (!string.IsNullOrEmpty(result.Message)) return result.Message;
      return GetString(result.Outcome switch
      {
        KeeShareOutcome.Failed => Resource.String.KeeShareFailed,
        KeeShareOutcome.Imported => Resource.String.KeeShareImportedChanges,
        KeeShareOutcome.Exported => Resource.String.export_database_successful,
        KeeShareOutcome.ImportedAndExported => Resource.String.SynchronizedDatabaseSuccessfully,
        KeeShareOutcome.Unchanged => Resource.String.RemoteDatabaseUnchanged,
        _ => Resource.String.keeshare_type_inactive
      });
    }

    private sealed class RowsAdapter : BaseAdapter
    {
      private readonly View[] _rows;
      public RowsAdapter(View[] rows) { _rows = rows; }
      public override int Count => _rows.Length;
      public override Java.Lang.Object GetItem(int position) => position;
      public override long GetItemId(int position) => position;
      public override View GetView(int position, View convertView, ViewGroup parent) => _rows[position];
    }
  }
}
