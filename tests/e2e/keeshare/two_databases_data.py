"""Synthetic cloned local databases and persisted-output oracles for two-DB E2E.

Only fixture preparation and independent KDBX inspection run on the host.
All synchronization, entry edits and deletion run in the Android app.
"""
import base64
from pathlib import Path
import uuid

from lxml import etree
from pykeepass import PyKeePass

from make_fixtures import make_fixtures

TITLE_A = 'Shared Owner A'
TITLE_B = 'Shared Owner B'
EDITED_B = 'Shared Owner B Edited'
RELOADED_A = 'Shared Owner A Reloaded'


def prepare(outdir):
    make_fixtures(outdir)
    main = PyKeePass(outdir / 'main.kdbx', password='main-pass')
    main.database_name = 'Owner A'
    entry = main.find_entries(title='Personal Entry', first=True)
    entry.title = TITLE_A
    recycle = main.add_group(main.root_group, 'Recycle Bin', icon='43')
    main.tree.find('Meta/RecycleBinEnabled').text = 'True'
    main.tree.find('Meta/RecycleBinUUID').text = base64.b64encode(recycle.uuid.bytes).decode()
    personal = main.find_groups(name='Personal', first=True)
    data = etree.SubElement(personal._element, 'CustomData')
    item = etree.SubElement(data, 'Item')
    etree.SubElement(item, 'Key').text = 'KeeShare/Reference'
    reference = ('<KeeShare><Type><Export/></Type><Group>'
                 + base64.b64encode(personal.uuid.bytes).decode()
                 + '</Group><Path>' + base64.b64encode(b'personal-export.kdbx.share').decode()
                 + '</Path><Password>' + base64.b64encode(b'exp-pass').decode()
                 + '</Password><KeepGroups>True</KeepGroups></KeeShare>')
    etree.SubElement(item, 'Value').text = base64.b64encode(reference.encode()).decode()
    main.save()
    # Clone after serialization so entry and group UUIDs/creation times coincide.
    clone_path = outdir / 'clone.kdbx'
    clone_path.write_bytes((outdir / 'main.kdbx').read_bytes())
    clone = PyKeePass(clone_path, password='main-pass')
    clone.database_name = 'Owner B'
    clone.find_entries(title=TITLE_A, first=True).title = TITLE_B
    for group in clone.groups:
        for custom in group._element.findall('CustomData/Item'):
            if custom.findtext('Key') == 'KeeShare/Reference':
                custom.getparent().remove(custom)
    clone.save()
    original = main.find_entries(title=TITLE_A, first=True)
    other = clone.find_entries(title=TITLE_B, first=True)
    assert original.uuid == other.uuid and original.ctime == other.ctime
    assert original.parentgroup.uuid == other.parentgroup.uuid
    return str(original.uuid)


def database(path):
    return PyKeePass(Path(path), password='main-pass')


def entry_by_uuid(db, entry_uuid):
    matches = [entry for entry in db.entries if str(entry.uuid) == entry_uuid]
    assert len(matches) <= 1, 'Duplicate UUID within one database'
    return matches[0] if matches else None


def assert_entry(path, entry_uuid, title, parent='Personal'):
    entry = entry_by_uuid(database(path), entry_uuid)
    assert entry is not None, 'Missing entry: ' + title
    assert entry.title == title and entry.parentgroup.name == parent, 'Wrong title/owner placement'
    return entry


def tombstoned(path, entry_uuid):
    db = database(path)
    encoded = base64.b64encode(uuid.UUID(entry_uuid).bytes).decode()
    return any(node.findtext('UUID') == encoded for node in db.tree.findall('Root/DeletedObjects/DeletedObject'))
