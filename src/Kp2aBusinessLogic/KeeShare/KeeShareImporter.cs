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

using System.Security.Cryptography;
using KeePassLib;
using KeePassLib.Interfaces;
using KeePassLib.Keys;
using KeePassLib.Serialization;

namespace keepass2android.KeeShare;

public static class KeeShareImporter
{
  internal static IEnumerable<IStructureItem> Descendants(PwGroup group) =>
    group.GetGroups(true).Cast<IStructureItem>().Concat(group.GetEntries(true));

  internal static string Fingerprint(PwGroup group) => KeeShareTreeFingerprint.Compute(
    Descendants(group).Select(item => (item.Uuid.ToHexString(), item.ParentGroup.Uuid.ToHexString(),
      item.LastModificationTime.Ticks, item.LocationChanged.Ticks,
      item is PwEntry entry ? (int)entry.History.UCount : 0)));

  internal static PwGroup CloneRoot(PwGroup source)
  {
    // CloneDeep keeps the original parent pointer; a database root must be detached.
    var clone = source.CloneDeep();
    var root = new PwGroup(false, false) { Uuid = clone.Uuid, IsExpanded = clone.IsExpanded,
      LocationChanged = clone.LocationChanged };
    root.AssignProperties(clone, false, true);
    foreach (var group in clone.Groups) root.AddGroup(group, true, false);
    foreach (var entry in clone.Entries) root.AddEntry(entry, true, false);
    return root;
  }

  internal static CompositeKey Key(string password)
  {
    var key = new CompositeKey();
    key.AddUserKey(new KcpPassword(password));
    return key;
  }

  internal static void CopyIcons(PwDatabase target, IEnumerable<PwCustomIcon> icons)
  {
    foreach (var icon in icons)
      if (target.GetCustomIconIndex(icon.Uuid) < 0) target.CustomIcons.Add(new PwCustomIcon(icon.Uuid, (byte[])icon.ImageDataPng.Clone())
        { Name = icon.Name, LastModificationTime = icon.LastModificationTime });
  }

  internal static IEnumerable<PwCustomIcon> UsedIcons(PwDatabase source, PwGroup root)
  {
    var used = root.GetGroups(true).Prepend(root).Select(group => group.CustomIconUuid)
      .Concat(root.GetEntries(true).SelectMany(entry => entry.History.Prepend(entry)).Select(entry => entry.CustomIconUuid))
      .ToHashSet();
    return source.CustomIcons.Where(icon => used.Contains(icon.Uuid)).ToArray();
  }

  // KDBX persists times at whole-second precision; local placement wins ties after reload.
  private static long WholeSeconds(DateTime time) => time.Ticks / TimeSpan.TicksPerSecond;

  private static bool SameOrigin(IStructureItem local, IStructureItem remote) =>
    local.GetType() == remote.GetType() && local.Uuid.Equals(remote.Uuid) &&
    // UUID alone cannot establish provenance.
    WholeSeconds(local.CreationTime) == WholeSeconds(remote.CreationTime);

  private static bool MovedOutside(IStructureItem local, IStructureItem remote)
  {
    // Moving a group leaves its descendants' LocationChanged untouched. Walk corresponding
    // ancestors to find the newer placement that carried the whole subtree out of the share.
    while (SameOrigin(local, remote))
    {
      if (local.ParentGroup == null || remote.ParentGroup == null) break;
      // A newer remote placement conflicts even when the parent UUID still matches.
      // Do not let an ancestor's local move-out silently discard that placement.
      if (WholeSeconds(remote.LocationChanged) > WholeSeconds(local.LocationChanged)) return false;
      if (!local.ParentGroup.Uuid.Equals(remote.ParentGroup.Uuid)) return true;
      local = local.ParentGroup;
      remote = remote.ParentGroup;
    }
    return false;
  }

  private static void ReconcileOutsideMoves(KeeShareGroup share, PwGroup remote)
  {
    var inside = Descendants(share.Group).Prepend(share.Group).Select(item => item.Uuid).ToHashSet();
    var outside = Descendants(share.Database.KpDatabase.RootGroup).Prepend(share.Database.KpDatabase.RootGroup)
      .Where(item => !inside.Contains(item.Uuid)).ToDictionary(item => item.Uuid);
    var moved = new List<IStructureItem>();
    foreach (var item in Descendants(remote))
    {
      if (!outside.TryGetValue(item.Uuid, out var local)) continue;
      if (!MovedOutside(local, item))
        throw new System.IO.InvalidDataException("KeeShare contains an item already present outside the shared group.");
      moved.Add(item);
    }
    // Validate every collision before pruning a moved group; it could contain an unrelated
    // collision. Only the decrypted remote copy is changed, never the locally owned objects.
    foreach (var item in moved)
    {
      if (item is PwGroup group) group.ParentGroup.Groups.Remove(group);
      else if (item is PwEntry entry) entry.ParentGroup.Entries.Remove(entry);
    }
  }

  private static void PreserveLocalSharingData(PwGroup localRoot, PwGroup mergedRoot)
  {
    var localGroups = localRoot.GetGroups(true).ToDictionary(group => group.Uuid);
    foreach (var group in mergedRoot.GetGroups(true))
    {
      // Sharing configuration belongs to this database. Never import remote device
      // credentials, including on newly added groups, or recreate a deleted local group.
      KeeShareGroups.StripSharingData(group);
      if (!localGroups.TryGetValue(group.Uuid, out var local) || !SameOrigin(local, group)) continue;
      foreach (var pair in local.CustomData.Where(pair => KeeShareGroups.IsSharingDataKey(pair.Key)))
        group.CustomData.Set(pair.Key, pair.Value);
    }
  }

  public static bool Import(IKp2aApp app, KeeShareGroup share, IOConnectionInfo ioc, IKp2aStatusLogger logger)
  {
    var storage = app.GetFileStorage(ioc, allowCache: false);
    Kp2aLog.Log("KeeShare: importing");
    byte[] bytes;
    using (var stream = storage.OpenFileForRead(ioc))
    using (var buffer = new MemoryStream())
    {
      stream.CopyTo(buffer);
      bytes = buffer.ToArray();
    }
    var hash = Convert.ToHexString(SHA256.HashData(bytes));
    var before = Fingerprint(share.Group);
    if (KeeShareScheduler.ImportUnchanged(share, ioc, hash, before)) return false;

    var remote = new PwDatabase();
    var scratch = new PwDatabase();
    try
    {
      // Load cleanup requires a root group even when the header or key is invalid.
      remote.New(new IOConnectionInfo(), Key(share.Reference.Password), "keeshare");
      using (var stream = new MemoryStream(KeeShareContainer.ExtractDatabase(bytes), writable: false))
        new KdbxFile(remote).Load(stream, KdbxFormat.Default, null);
      remote.RootGroup.Uuid = share.Group.Uuid;
      var remoteFingerprint = Fingerprint(remote.RootGroup);
      ReconcileOutsideMoves(share, remote.RootGroup);
      scratch.New(new IOConnectionInfo(), remote.MasterKey, "keeshare");
      scratch.RootGroup = CloneRoot(share.Group);
      CopyIcons(scratch, share.Database.KpDatabase.CustomIcons);
      CopyIcons(scratch, remote.CustomIcons);
      // Local tombstones prevent pre-export imports from resurrecting locally deleted entries.
      foreach (var deleted in share.Database.KpDatabase.DeletedObjects.GroupBy(deleted => deleted.Uuid)
                 .Select(group => group.OrderByDescending(deleted => deleted.DeletionTime).First()))
        scratch.DeletedObjects.Add(deleted.CloneDeep());
      scratch.MergeIn(remote, PwMergeMethod.Synchronize, null);
      PreserveLocalSharingData(share.Group, scratch.RootGroup);
      if (Fingerprint(scratch.RootGroup) == before)
      {
        KeeShareScheduler.RecordImport(share, ioc, hash, remoteFingerprint);
        return false;
      }

      // Check KeePass's depth limit in the real ancestor context before touching the live group.
      var targetDepth = share.Group.GetDepth();
      if (scratch.RootGroup.GetGroups(true).Any(group => targetDepth + group.GetDepth() > 126))
        throw new System.IO.InvalidDataException("KeeShare group nesting exceeds the database limit.");
      var previous = Descendants(share.Group).Select(item => item.Uuid).ToHashSet();
      var current = Descendants(scratch.RootGroup).Select(item => item.Uuid).ToHashSet();
      var outside = Descendants(share.Database.KpDatabase.RootGroup).Prepend(share.Database.KpDatabase.RootGroup)
        .Select(item => item.Uuid).Where(uuid => !previous.Contains(uuid) && !uuid.Equals(share.Group.Uuid)).ToHashSet();
      if (current.Overlaps(outside))
        throw new System.IO.InvalidDataException("KeeShare contains an item already present outside the shared group.");
      var icons = UsedIcons(scratch, scratch.RootGroup).ToArray();
      var deletedObjects = previous.Except(current).Select(uuid => new PwDeletedObject(uuid, DateTime.UtcNow)).ToArray();
      var groups = scratch.RootGroup.Groups.ToArray();
      var entries = scratch.RootGroup.Entries.ToArray();

      share.Group.Groups.Clear();
      share.Group.Entries.Clear();
      // Preserve merge timestamps; changing LocationChanged here would make repeated imports churn.
      foreach (var group in groups) share.Group.AddGroup(group, true, false);
      foreach (var entry in entries) share.Group.AddEntry(entry, true, false);
      foreach (var deleted in deletedObjects) share.Database.KpDatabase.DeletedObjects.Add(deleted);
      CopyIcons(share.Database.KpDatabase, icons);
      share.Database.KpDatabase.Modified = true;
      KeeShareScheduler.RecordImport(share, ioc, hash, remoteFingerprint);
      return true;
    }
    finally
    {
      scratch.Close();
      remote.Close();
    }
  }
}
