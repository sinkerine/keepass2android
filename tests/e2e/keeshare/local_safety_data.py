"""Synthetic inputs and independent persisted-output checks for local safety E2E.

This module never implements or invokes the KeeShare engine. Android performs all
imports, moves, recycling and exports; pykeepass only prepares files and reads them.
"""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from lxml import etree
from pykeepass import PyKeePass

from make_fixtures import make_fixtures
from journey_data import load_share, save_zip

OLD = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
TITLES = ('Move Outside Entry', 'Recycle Outside Entry', 'Nested Outside Entry')
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a6XcAAAAASUVORK5CYII=')


def location(item):
    return item._kp._decode_time(item._element.findtext('Times/LocationChanged'))


def set_location(item, value):
    item._element.find('Times/LocationChanged').text = item._kp._encode_time(value)


def fixed_times(item):
    item.ctime = OLD
    item.mtime = OLD
    item.atime = OLD
    set_location(item, OLD)


def add_icon(db, item):
    icon_uuid = uuid.uuid4()
    icons = db.tree.find('Meta/CustomIcons')
    if icons is None:
        icons = etree.SubElement(db.tree.find('Meta'), 'CustomIcons')
    icon = etree.SubElement(icons, 'Icon')
    etree.SubElement(icon, 'UUID').text = base64.b64encode(icon_uuid.bytes).decode()
    etree.SubElement(icon, 'Data').text = base64.b64encode(PNG).decode()
    etree.SubElement(item._element, 'CustomIconUUID').text = base64.b64encode(icon_uuid.bytes).decode()


def prepare(outdir):
    make_fixtures(outdir)
    main = PyKeePass(outdir / 'main.kdbx', password='main-pass')
    # Ensure the recycle operation has a known, visible destination from the start.
    recycle = main.add_group(main.root_group, 'Recycle Bin', icon='43')
    main.tree.find('Meta/RecycleBinEnabled').text = 'True'
    main.tree.find('Meta/RecycleBinUUID').text = base64.b64encode(recycle.uuid.bytes).decode()
    control = main.add_entry(main.find_groups(name='Team Sync', first=True),
                             'Atomic Inside Control', 'synthetic', 'synthetic')
    fixed_times(control)
    main.save()
    remote = load_share(outdir / 'team-sync.kdbx.share')
    for title in TITLES[:2]:
        entry = remote.add_entry(remote.root_group, title, 'synthetic', 'synthetic')
        fixed_times(entry)
        add_icon(remote, entry)
    group = remote.add_group(remote.root_group, 'Move Outside Group')
    fixed_times(group)
    nested = remote.add_group(group, 'Outside Deep Group')
    fixed_times(nested)
    entry = remote.add_entry(nested, TITLES[2], 'synthetic', 'synthetic')
    fixed_times(entry)
    add_icon(remote, entry)
    save_zip(remote, outdir / 'team-sync.kdbx.share')


def normalized_element(db, element):
    """Compare full decrypted XML, decoding only the KDBX time representation."""
    element = deepcopy(element)
    for node in element.iter():
        if node.tag in ('CreationTime', 'LastModificationTime', 'LastAccessTime',
                        'ExpiryTime', 'LocationChanged', 'DeletionTime') and node.text:
            node.text = db._decode_time(node.text).isoformat()
    return etree.tostring(element, method='c14n')


def full_state(db):
    return normalized_element(db, db.tree.getroot())


def icons_and_tombstones(db):
    return {name: (normalized_element(db, db.tree.find(path))
                   if db.tree.find(path) is not None else None)
            for name, path in (('icons', 'Meta/CustomIcons'),
                               ('tombstones', 'Root/DeletedObjects'))}


def find_uuid(db, item_uuid):
    objects = list(db.groups) + list(db.entries)
    matches = [item for item in objects if item.uuid == item_uuid]
    assert len(matches) == 1, f'Expected one object for {item_uuid}, found {len(matches)}'
    return matches[0]


def protected_state(db):
    personal = db.find_groups(name='Personal', first=True)
    recycle = db.find_groups(name='Recycle Bin', first=True)
    expected = {TITLES[0]: personal, TITLES[1]: recycle}
    protected = {}
    for title, parent in expected.items():
        entry = db.find_entries(title=title, first=True)
        assert entry is not None and entry.parentgroup.uuid == parent.uuid, title + ' placement differs'
        assert find_uuid(db, entry.uuid).title == title
        protected[str(entry.uuid)] = normalized_element(db, entry._element)
    group = db.find_groups(name='Move Outside Group', first=True)
    assert group is not None and group.parentgroup.uuid == personal.uuid, 'Moved group placement differs'
    assert find_uuid(db, group.uuid).name == group.name
    entry = db.find_entries(title=TITLES[2], first=True)
    assert entry is not None and entry.parentgroup.parentgroup.uuid == group.uuid
    for descendant in [group] + list(group.subgroups) + list(group.entries) + list(entry.parentgroup.entries):
        find_uuid(db, descendant.uuid)
    protected[str(group.uuid)] = normalized_element(db, group._element)
    return protected


def assert_preserved(before, after):
    assert protected_state(after) == protected_state(before), 'Outside objects changed or were duplicated'
    assert icons_and_tombstones(after) == icons_and_tombstones(before), 'Icons/tombstones changed'


def assert_export_excludes(remote, baseline):
    excluded = set(protected_state(baseline))
    group = baseline.find_groups(name='Move Outside Group', first=True)
    excluded.update(str(item.uuid) for item in baseline.groups + baseline.entries
                    if item._element is not group._element and group._element in item._element.iterancestors())
    actual = {str(item.uuid) for item in remote.groups + remote.entries}
    assert not excluded.intersection(actual), 'Export resurrected outside/recycled objects'


def remote_input(stale_path, destination, baseline, *, marker, placement='older', collision=None):
    remote = load_share(stale_path)
    if placement == 'equal':
        for title in TITLES[:2]:
            source = baseline.find_entries(title=title, first=True)
            set_location(remote.find_entries(title=title, first=True), location(source))
        local_group = baseline.find_groups(name='Move Outside Group', first=True)
        set_location(remote.find_groups(name=local_group.name, first=True), location(local_group))
    elif placement != 'older':
        raise ValueError(placement)
    if collision == 'newer-entry':
        local = baseline.find_entries(title=TITLES[0], first=True)
        set_location(remote.find_entries(title=TITLES[0], first=True), location(local) + timedelta(seconds=60))
    elif collision == 'newer-descendant':
        local = baseline.find_entries(title=TITLES[2], first=True)
        set_location(remote.find_entries(title=TITLES[2], first=True), location(local) + timedelta(seconds=60))
    elif collision == 'different-creation':
        entry = remote.find_entries(title=TITLES[0], first=True)
        entry.ctime = OLD + timedelta(days=1)
    elif collision == 'different-type':
        entry = remote.find_entries(title=TITLES[0], first=True)
        entry_uuid = entry.uuid
        remote.delete_entry(entry)
        group = remote.add_group(remote.root_group, 'Conflicting Object Type')
        group.uuid = entry_uuid
        fixed_times(group)
    elif collision is not None:
        raise ValueError(collision)
    fresh = remote.add_entry(remote.root_group, marker, 'synthetic', 'synthetic')
    if collision:
        # All must remain absent if collision validation is atomic.
        add_icon(remote, fresh)
        control = baseline.find_entries(title='Atomic Inside Control', first=True)
        deleted = remote.tree.find('Root/DeletedObjects')
        if deleted is None:
            deleted = etree.SubElement(remote.tree.find('Root'), 'DeletedObjects')
        tombstone = etree.SubElement(deleted, 'DeletedObject')
        etree.SubElement(tombstone, 'UUID').text = base64.b64encode(control.uuid.bytes).decode()
        etree.SubElement(tombstone, 'DeletionTime').text = remote._encode_time(datetime.now(timezone.utc) + timedelta(days=1))
    save_zip(remote, destination)
    # Fixture contract, not an engine simulation: prove intended inputs survived KDBX serialization.
    reopened = load_share(destination)
    assert reopened.find_entries(title=marker, first=True) is not None
    if collision == 'different-type':
        local = baseline.find_entries(title=TITLES[0], first=True)
        actual = find_uuid(reopened, local.uuid)
        assert actual._element.tag == 'Group' and actual.ctime == local.ctime
    elif collision == 'different-creation':
        actual = reopened.find_entries(title=TITLES[0], first=True)
        assert actual.uuid == baseline.find_entries(title=TITLES[0], first=True).uuid
        assert actual.ctime == OLD + timedelta(days=1)
    elif collision in ('newer-entry', 'newer-descendant'):
        title = TITLES[0] if collision == 'newer-entry' else TITLES[2]
        actual = reopened.find_entries(title=title, first=True)
        local = baseline.find_entries(title=title, first=True)
        assert actual.uuid == local.uuid and actual.ctime == local.ctime
        assert location(actual) == location(local) + timedelta(seconds=60)
    elif placement == 'equal':
        for title in TITLES[:2]:
            assert location(reopened.find_entries(title=title, first=True)) == location(
                baseline.find_entries(title=title, first=True))
        assert location(reopened.find_groups(name='Move Outside Group', first=True)) == location(
            baseline.find_groups(name='Move Outside Group', first=True))
    else:
        for title in TITLES[:2]:
            assert location(reopened.find_entries(title=title, first=True)) < location(
                baseline.find_entries(title=title, first=True))
    return Path(destination)
