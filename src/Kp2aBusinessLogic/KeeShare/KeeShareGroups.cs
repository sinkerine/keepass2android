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
using KeePassLib;
using KeePassLib.Interfaces;
using KeePassLib.Serialization;

namespace keepass2android.KeeShare;

public sealed class KeeShareGroup
{
  public Database Database { get; }
  public PwGroup Group { get; }
  public KeeShareReference Reference { get; }

  public KeeShareGroup(Database database, PwGroup group, KeeShareReference reference)
  {
    Database = database;
    Group = group;
    Reference = reference;
  }
}

public static class KeeShareGroups
{
  private static readonly ConditionalWeakTable<PwDatabase, HashSet<PwUuid>> _invalidReferences = new();

  private static KeeShareGroup? Read(Database db, PwGroup group)
  {
    var value = group.CustomData.Get(KeeShareReferenceCodec.CustomDataKey);
    if (value == null) return null;
    if (KeeShareReferenceCodec.TryDecode(value, out var reference))
      return new KeeShareGroup(db, group, reference);
    var invalid = _invalidReferences.GetOrCreateValue(db.KpDatabase);
    lock (invalid)
      if (invalid.Add(group.Uuid)) Kp2aLog.Log("KeeShare: invalid reference on group " + group.Name);
    return null;
  }

  public static IReadOnlyList<KeeShareGroup> Find(Database db)
  {
    if (db.KpDatabase?.RootGroup == null) return Array.Empty<KeeShareGroup>();
    return db.KpDatabase.RootGroup.GetGroups(true).Prepend(db.KpDatabase.RootGroup)
      .Select(group => Read(db, group)).OfType<KeeShareGroup>().ToArray();
  }

  public static KeeShareGroup? FindShareFor(Database db, PwGroup group)
  {
    for (var current = group; current != null; current = current.ParentGroup)
    {
      var share = Read(db, current);
      if (share != null) return share;
    }
    return null;
  }

  public static bool IsReadOnlyContent(Database db, PwGroup group)
  {
    // An enclosing Import-only share remains read-only even if a descendant has a reference.
    for (var current = group; current != null; current = current.ParentGroup)
      if (Read(db, current)?.Reference.Type == KeeShareType.Import) return true;
    return false;
  }

  public static bool BlocksModification(Database db, IEnumerable<IStructureItem> items, PwGroup? target) =>
    (target != null && IsReadOnlyContent(db, target)) || items.Any(item =>
      (item is PwGroup group && IsReadOnlyContent(db, group)) ||
      (item.ParentGroup != null && IsReadOnlyContent(db, item.ParentGroup)));

  public static void SetReference(PwGroup group, KeeShareReference reference)
  {
    group.CustomData.Set(KeeShareReferenceCodec.CustomDataKey, KeeShareReferenceCodec.Encode(reference));
    group.Touch(true, false);
  }

  internal static bool IsSharingDataKey(string key) =>
    key == KeeShareReferenceCodec.CustomDataKey || key.StartsWith("KP2A/KeeShare/", StringComparison.Ordinal);

  // Clone sanitization must preserve modification/access times and usage counts.
  internal static void StripSharingData(PwGroup group)
  {
    foreach (var key in group.CustomData.Select(pair => pair.Key).Where(IsSharingDataKey).ToArray())
      group.CustomData.Remove(key);
  }

  public static void RemoveReference(PwGroup group)
  {
    StripSharingData(group);
    group.Touch(true, false);
  }

  public static IOConnectionInfo? GetDeviceIoc(PwGroup group, string deviceId)
  {
    var value = group.CustomData.Get(KeeSharePath.DeviceIocKey(deviceId));
    if (string.IsNullOrEmpty(value)) return null;
    try { return IOConnectionInfo.UnserializeFromString(value); }
    catch (ArgumentException) { return null; }
    catch (FormatException) { return null; }
  }

  public static void SetDeviceIoc(PwGroup group, string deviceId, IOConnectionInfo? ioc)
  {
    var key = KeeSharePath.DeviceIocKey(deviceId);
    if (ioc == null) group.CustomData.Remove(key);
    else
    {
      var stored = ioc.CloneDeep();
      stored.CredSaveMode = IOCredSaveMode.SaveCred;
      group.CustomData.Set(key, IOConnectionInfo.SerializeToString(stored));
    }
    group.Touch(true, false);
  }
}
