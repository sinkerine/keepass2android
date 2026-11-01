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

using KeePassLib;
using KeePassLib.Serialization;

namespace keepass2android.KeeShare;

public static class KeeShareExporter
{
  public static void Export(IKp2aApp app, KeeShareGroup share, IOConnectionInfo ioc, IKp2aStatusLogger logger)
  {
    var storage = app.GetFileStorage(ioc, allowCache: false);
    Kp2aLog.Log("KeeShare: exporting");
    var export = new PwDatabase();
    try
    {
      export.New(new IOConnectionInfo(), KeeShareImporter.Key(share.Reference.Password), share.Group.Name);
      export.RootGroup = KeeShareImporter.CloneRoot(share.Group);
      if (!share.Reference.KeepGroups) export.RootGroup.Groups.Clear();
      foreach (var group in export.RootGroup.GetGroups(true).Prepend(export.RootGroup))
        KeeShareGroups.StripSharingData(group);
      export.RecycleBinEnabled = false;
      export.Name = share.Group.Name;
      KeeShareImporter.CopyIcons(export, KeeShareImporter.UsedIcons(share.Database.KpDatabase, export.RootGroup));
      foreach (var deleted in share.Database.KpDatabase.DeletedObjects)
        export.DeletedObjects.Add(deleted.CloneDeep());
      byte[] bytes;
      using (var stream = new MemoryStream())
      {
        new KdbxFile(export).Save(stream, null, KdbxFormat.Default, null);
        bytes = KeeShareContainer.WrapForWrite(stream.ToArray(), KeeShareContainer.KindForWrite(ioc.Path));
      }
      var fingerprint = KeeShareImporter.Fingerprint(share.Group);
      using (var transaction = storage.OpenWriteTransaction(ioc,
               app.GetBooleanPreference(PreferenceKey.UseFileTransactions)))
      {
        using (var stream = transaction.OpenFile()) stream.Write(bytes, 0, bytes.Length);
        transaction.CommitWrite();
      }
      KeeShareScheduler.RecordExport(share, ioc, fingerprint);
    }
    finally { export.Close(); }
  }
}
