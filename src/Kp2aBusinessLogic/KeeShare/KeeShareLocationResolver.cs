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

using KeePassLib.Serialization;
using keepass2android.Io;

namespace keepass2android.KeeShare;

public enum KeeShareLocationProblem { None, NotSet, SmbCredentialsNeeded, StorageUnavailable, Offline }

public static class KeeShareLocationResolver
{
  public static IOConnectionInfo? Resolve(IKp2aApp app, KeeShareGroup share, string deviceId,
    out KeeShareLocationProblem problem)
  {
    problem = KeeShareLocationProblem.NotSet;
    try
    {
      var location = KeeSharePath.Choose(share.Group.CustomData.Get(KeeSharePath.DeviceIocKey(deviceId)),
        share.Reference.Path, GetMounts(share.Database, deviceId));
      IOConnectionInfo ioc;
      switch (location)
      {
        case KeeShareLocation.DeviceIoc device:
          ioc = IOConnectionInfo.UnserializeFromString(device.SerializedIoc);
          break;
        case KeeShareLocation.Mapped mapped:
          ioc = IOConnectionInfo.UnserializeFromString(mapped.SerializedFolderIoc);
          if (CheckOffline(ioc, out problem)) return null;
          ioc = Append(app.GetFileStorage(ioc, allowCache: false), ioc, mapped.Segments);
          break;
        case KeeShareLocation.Unc unc:
          var path = KeeShareSmbPath.BorrowCredentials(share.Database.Ioc.Path, unc.Host, unc.Share, unc.Segments);
          if (path == null)
          {
            problem = KeeShareLocationProblem.SmbCredentialsNeeded;
            return null;
          }
          ioc = IOConnectionInfo.FromPath(path);
          break;
        case KeeShareLocation.RelativeToDatabase relative:
          ioc = share.Database.Ioc;
          if (CheckOffline(ioc, out problem)) return null;
          var storage = app.GetFileStorage(ioc, allowCache: false);
          ioc = Append(storage, storage.GetParentPath(ioc), relative.Segments);
          break;
        default:
          return null;
      }
      if (string.IsNullOrEmpty(ioc.Path)) return null;
      if (CheckOffline(ioc, out problem)) return null;
      app.GetFileStorage(ioc, allowCache: false);
      problem = KeeShareLocationProblem.None;
      return ioc;
    }
    catch (Java.Lang.InterruptedException) { throw; }
    catch (Java.IO.InterruptedIOException) { throw; }
    catch (NoFileStorageFoundException) { problem = KeeShareLocationProblem.StorageUnavailable; }
    catch (Exception) { problem = KeeShareLocationProblem.NotSet; }
    return null;
  }

  private static bool CheckOffline(IOConnectionInfo ioc, out KeeShareLocationProblem problem)
  {
    problem = !ioc.IsLocalFile() && KeeShareScheduler.IsOffline()
      ? KeeShareLocationProblem.Offline : KeeShareLocationProblem.NotSet;
    return problem == KeeShareLocationProblem.Offline;
  }

  private static IOConnectionInfo Append(IFileStorage storage, IOConnectionInfo folder, IEnumerable<string> segments)
  {
    foreach (var segment in segments) folder = storage.GetFilePath(folder, segment);
    return folder;
  }

  public static KeeShareMountMap GetMounts(Database db, string deviceId) =>
    KeeShareMountMap.Decode(db.KpDatabase.CustomData.Get(KeeShareMountMap.DatabaseCustomDataKeyPrefix + deviceId));

  public static void SetMounts(Database db, string deviceId, KeeShareMountMap mounts)
  {
    db.KpDatabase.CustomData.Set(KeeShareMountMap.DatabaseCustomDataKeyPrefix + deviceId, mounts.Encode());
    db.KpDatabase.Modified = true;
  }
}
