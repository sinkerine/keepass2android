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
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Android.App;
using Android.Content;
using KeePass.Util;
using KeePassLib.Cryptography;
using KeePassLib.Serialization;
using KeePassLib.Utility;
using keepass2android.Io;

namespace keepass2android
{
  public class CheckDatabaseForChanges : OperationWithFinishHandler
  {
    private readonly IKp2aApp _app;
    private readonly Database _database;
    private readonly Action<Database> _onReloadRequired;

    // A successful check can still require a reload before the in-memory data is current.
    public bool ReloadPending { get; private set; }

    public CheckDatabaseForChanges(IKp2aApp app, OnOperationFinishedHandler operationFinishedHandler)
        : this(app, app.CurrentDb, operationFinishedHandler, database => app.TriggerReload(null, null))
    {
    }

    public CheckDatabaseForChanges(IKp2aApp app, Database database,
        OnOperationFinishedHandler operationFinishedHandler, Action<Database> onReloadRequired)
        : base(app, operationFinishedHandler)
    {
      _app = app;
      _database = database;
      _onReloadRequired = onReloadRequired;
    }

    public override void Run()
    {
      try
      {
        IOConnectionInfo ioc = _database.Ioc;
        IFileStorage fileStorage = _app.GetFileStorage(ioc);
        if (fileStorage is CachingFileStorage)
        {
          throw new Exception("Cannot sync a cached database!");
        }
        StatusLogger.UpdateMessage(UiStringKey.CheckingDatabaseForChanges);

        //download file from remote location and calculate hash:
        StatusLogger.UpdateSubMessage(_app.GetResourceString(UiStringKey.DownloadingRemoteFile));


        MemoryStream remoteData = new MemoryStream();
        using (
            HashingStreamEx hashingRemoteStream = new HashingStreamEx(fileStorage.OpenFileForRead(ioc), false,
                                                                        new SHA256Managed()))
        {
          hashingRemoteStream.CopyTo(remoteData);
          hashingRemoteStream.Close();

          if (!MemUtil.ArraysEqual(_database.KpDatabase.HashOfFileOnDisk, hashingRemoteStream.Hash))
          {
            ReloadPending = true;
            _onReloadRequired?.Invoke(_database);
            Finish(true);
          }
          else
          {
            Finish(true, _app.GetResourceString(UiStringKey.RemoteDatabaseUnchanged));
          }
        }



      }
      catch (Exception e)
      {
        Finish(false, ExceptionUtil.GetErrorMessage(e));
      }

    }

  }
}
