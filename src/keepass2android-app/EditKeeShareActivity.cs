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
using Android.App;
using Android.Content;
using Android.Content.PM;
using Android.OS;
using Android.Views;
using Android.Widget;
using keepass2android.Io;
using keepass2android.KeeShare;
using KeePassLib;
using KeePassLib.Serialization;
using KeePassLib.Utility;

namespace keepass2android
{
  [Activity(Label = "@string/menu_keeshare", Theme = "@style/Kp2aTheme_BlueActionBar", ConfigurationChanges = ConfigChanges.Orientation | ConfigChanges.Keyboard | ConfigChanges.KeyboardHidden)]
  public class EditKeeShareActivity : LockCloseActivity
  {
    public const string EXTRA_GROUP_UUID = "EXTRA_GROUP_UUID";
    private const string ExtraDatabaseIoc = "EXTRA_DATABASE_IOC";
    private const int PickDeviceFile = 1;
    private Database _database;
    private PwGroup _group;
    private IOConnectionInfo _deviceIoc;
    private KeeShareMountMap.Mount _derivedMount;
    private Spinner _type;
    private EditText _path;
    private EditText _password;
    private CheckBox _keepGroups;
    private CheckBox _rememberMount;
    private bool _saving;
    private bool _passwordNeedsReentry;

    // The share root's configuration remains editable so Import can be changed or removed.
    // A descendant of an Import share is still protected.
    internal static bool CanConfigure(Database database, PwGroup group) => database != null && database.CanWrite &&
      (group.ParentGroup == null || !KeeShareGroups.IsReadOnlyContent(database, group.ParentGroup));

    public static void Launch(Activity activity, Database database, PwGroup group)
    {
      var intent = new Intent(activity, typeof(EditKeeShareActivity));
      intent.PutExtra(EXTRA_GROUP_UUID, group.Uuid.ToHexString());
      intent.PutExtra(ExtraDatabaseIoc, IOConnectionInfo.SerializeToString(database.Ioc));
      activity.StartActivity(intent);
    }

    protected override void OnCreate(Bundle savedInstanceState)
    {
      base.OnCreate(savedInstanceState);
      try
      {
        _database = App.Kp2a.TryGetDatabase(IOConnectionInfo.UnserializeFromString(Intent.GetStringExtra(ExtraDatabaseIoc)));
        var uuid = new PwUuid(MemUtil.HexStringToByteArray(Intent.GetStringExtra(EXTRA_GROUP_UUID)));
        if (_database == null || !_database.GroupsById.TryGetValue(uuid, out _group)) { Finish(); return; }
      }
      catch (Exception) { Finish(); return; }
      _ioc = _database.Ioc;
      if (!CanConfigure(_database, _group))
      {
        App.Kp2a.ShowMessage(this, Resource.String.keeshare_readonly_info_label, MessageSeverity.Info);
        Finish();
        return;
      }
      SetContentView(Resource.Layout.edit_keeshare);
      _type = FindViewById<Spinner>(Resource.Id.keeshare_type_spinner);
      _path = FindViewById<EditText>(Resource.Id.keeshare_path);
      _password = FindViewById<EditText>(Resource.Id.keeshare_password);
      _keepGroups = FindViewById<CheckBox>(Resource.Id.keeshare_keep_groups);
      _rememberMount = FindViewById<CheckBox>(Resource.Id.keeshare_remember_mount);
      if (KeeShareReferenceCodec.TryDecode(_group.CustomData.Get(KeeShareReferenceCodec.CustomDataKey), out var reference))
      {
        _type.SetSelection((int)reference.Type);
        _path.Text = reference.Path;
        // Password view state is deliberately disabled; never restore an old password over a lost draft.
        if (savedInstanceState == null) _password.Text = reference.Password;
        _keepGroups.Checked = reference.KeepGroups;
      }
      else _type.SetSelection((int)KeeShareType.Import);
      _passwordNeedsReentry = savedInstanceState != null;
      if (_passwordNeedsReentry) _password.Hint = GetString(Resource.String.keeshare_password_reentry);
      _deviceIoc = KeeShareGroups.GetDeviceIoc(_group, KeeAutoExecExt.ThisDeviceId);
      if (savedInstanceState?.ContainsKey("deviceIoc") == true)
      {
        var value = savedInstanceState.GetString("deviceIoc");
        _deviceIoc = string.IsNullOrEmpty(value) ? null : IOConnectionInfo.UnserializeFromString(value);
      }
      UpdateDeviceLabel();
      _path.TextChanged += (sender, args) => DeriveMount();
      FindViewById<Button>(Resource.Id.keeshare_pick_device_file).Click += (sender, args) =>
      {
        var exporting = ((KeeShareType)_type.SelectedItemPosition & KeeShareType.Export) != 0;
        var intent = new Intent(this, typeof(SelectStorageLocationActivity));
        intent.PutExtra(SelectStorageLocationActivity.ExtraKeyWritableRequirements, (int)(exporting
          ? SelectStorageLocationActivityBase.WritableRequirements.WriteDemanded
          : SelectStorageLocationActivityBase.WritableRequirements.ReadOnly));
        intent.PutExtra(FileStorageSetupDefs.ExtraIsForSave, exporting);
        StartActivityForResult(intent, PickDeviceFile);
      };
      FindViewById<Button>(Resource.Id.keeshare_clear_device_file).Click += (sender, args) =>
      {
        _deviceIoc = null;
        UpdateDeviceLabel();
        DeriveMount();
      };
      FindViewById<Button>(Resource.Id.keeshare_save).Click += (sender, args) => Save(false);
      var remove = FindViewById<Button>(Resource.Id.keeshare_remove);
      remove.Enabled = _group.CustomData.Get(KeeShareReferenceCodec.CustomDataKey) != null;
      remove.Click += (sender, args) => Save(true);
    }

    protected override void OnSaveInstanceState(Bundle outState)
    {
      base.OnSaveInstanceState(outState);
      outState.PutString("deviceIoc", _deviceIoc == null ? "" : IOConnectionInfo.SerializeToString(_deviceIoc));
      outState.PutBoolean("rememberMount", _derivedMount != null);
      outState.PutBoolean("rememberMountChecked", _rememberMount?.Checked == true);
    }

    protected override void OnRestoreInstanceState(Bundle savedInstanceState)
    {
      base.OnRestoreInstanceState(savedInstanceState);
      if (savedInstanceState.GetBoolean("rememberMount"))
      {
        DeriveMount();
        _rememberMount.Checked = savedInstanceState.GetBoolean("rememberMountChecked");
      }
    }

    protected override void OnActivityResult(int requestCode, Result resultCode, Intent data)
    {
      base.OnActivityResult(requestCode, resultCode, data);
      if (requestCode != PickDeviceFile || resultCode != Result.Ok || data == null) return;
      _deviceIoc = new IOConnectionInfo();
      Util.SetIoConnectionFromIntent(_deviceIoc, data);
      UpdateDeviceLabel();
      DeriveMount();
    }

    private void UpdateDeviceLabel()
    {
      string label = GetString(Resource.String.KeeShareLocationNotSet);
      if (_deviceIoc != null)
      {
        try { label = App.Kp2a.GetFileStorage(_deviceIoc).GetDisplayName(_deviceIoc); }
        catch (Exception) { label = GetString(Resource.String.KeeShareStorageUnavailable); }
      }
      FindViewById<TextView>(Resource.Id.keeshare_device_file_label).Text = label;
    }

    private void DeriveMount()
    {
      _derivedMount = null;
      _rememberMount.Visibility = ViewStates.Gone;
      if (_deviceIoc == null) return;
      try
      {
        var storage = App.Kp2a.GetFileStorage(_deviceIoc);
        if (!KeeShareMountMap.TryDerive(_path.Text, KeeSharePath.Segments(storage.GetDisplayName(_deviceIoc)),
          out var prefix, out var parentSteps)) return;
        var folder = _deviceIoc.CloneDeep();
        for (int i = 0; i < parentSteps; i++) folder = storage.GetParentPath(folder);
        folder.CredSaveMode = IOCredSaveMode.SaveCred;
        _derivedMount = new KeeShareMountMap.Mount(prefix, IOConnectionInfo.SerializeToString(folder));
        _rememberMount.Text = GetString(Resource.String.KeeShareRememberMount, storage.GetDisplayName(folder), prefix);
        _rememberMount.Checked = true;
        _rememberMount.Visibility = ViewStates.Visible;
      }
      catch (Exception) { /* A location can still be saved when its provider cannot derive a parent. */ }
    }

    private void Save(bool remove)
    {
      if (_saving || !CanConfigure(_database, _group)) return;
      if (!remove && _passwordNeedsReentry)
      {
        var password = new EditText(this)
        {
          InputType = Android.Text.InputTypes.ClassText | Android.Text.InputTypes.TextVariationPassword,
          SaveEnabled = false,
          Text = _password.Text
        };
        new Google.Android.Material.Dialog.MaterialAlertDialogBuilder(this)
          .SetMessage(Resource.String.keeshare_password_reentry)
          .SetView(password)
          .SetPositiveButton(Android.Resource.String.Ok, (sender, args) =>
          {
            _password.Text = password.Text;
            _passwordNeedsReentry = false;
            Save(false);
          })
          .SetNegativeButton(Android.Resource.String.Cancel, (sender, args) => { })
          .Show();
        return;
      }
      _saving = true;
      var locker = new BackgroundDatabaseModificationLocker(App.Kp2a);
      locker.BeforeModifyDatabases();
      try
      {
        if (remove) KeeShareGroups.RemoveReference(_group);
        else
        {
          KeeShareGroups.SetReference(_group, new KeeShareReference((KeeShareType)_type.SelectedItemPosition,
            _group.Uuid.UuidBytes, _path.Text, _password.Text, _keepGroups.Checked));
          KeeShareGroups.SetDeviceIoc(_group, KeeAutoExecExt.ThisDeviceId, _deviceIoc);
          if (_derivedMount != null && _rememberMount.Checked)
            KeeShareLocationResolver.SetMounts(_database, KeeAutoExecExt.ThisDeviceId,
              KeeShareLocationResolver.GetMounts(_database, KeeAutoExecExt.ThisDeviceId).With(_derivedMount));
        }
        _database.KpDatabase.Modified = true;
      }
      finally { locker.AfterModifyDatabases(); }
      new BlockingOperationStarter(App.Kp2a, new SaveDb(App.Kp2a, _database,
        new ActionInContextInstanceOnOperationFinished(ContextInstanceId, App.Kp2a, (success, message, context) =>
        {
          if (context is EditKeeShareActivity activity)
          {
            activity._saving = false;
            if (success) activity.Finish();
            else if (!string.IsNullOrEmpty(message)) App.Kp2a.ShowMessage(context, message, MessageSeverity.Error);
          }
        }))).Run();
    }
  }
}
