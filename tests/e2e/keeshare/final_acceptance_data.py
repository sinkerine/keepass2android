"""Independent inputs and persisted KDBX oracles for the final four checks."""
import base64
from copy import deepcopy
from lxml import etree
from pykeepass import PyKeePass, create_database
from make_fixtures import set_reference
from journey_data import custom, put_custom

IOC_PREFIX = 'KP2A/KeeShare/Ioc/'
MARKER = 'Final Picked Empty Path Marker'


def database(path):
    return PyKeePass(path, password='main-pass')


def group(db, name):
    result = db.find_groups(name=name, first=True)
    assert result is not None, 'Missing group: ' + name
    return result


def reference(target):
    return etree.fromstring(base64.b64decode(custom(target)['KeeShare/Reference']))


def export_reference(target, path, keep_groups):
    set_reference(target, path, synchronize=True, keep_groups=keep_groups)
    item = target._element.find('CustomData/Item/Value')
    xml = etree.fromstring(base64.b64decode(item.text))
    xml.find('Type').remove(xml.find('Type/Import'))
    item.text = base64.b64encode(etree.tostring(xml)).decode()


def parent(path):
    db = create_database(path, password='main-pass')
    for name in ('Team Import', 'Team Sync', 'Personal'):
        db.add_group(db.root_group, name)
    return db


def prepare(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    move = parent(outdir / 'move-parent.kdbx')
    set_reference(group(move, 'Team Import'), 'move-share.kdbx', keep_groups=True)
    move.add_entry(group(move, 'Personal'), 'Ordinary Move Candidate', 'synthetic', 'synthetic')
    move.save()
    remote = create_database(outdir / 'move-share.kdbx', password='share-pass')
    remote.add_entry(remote.root_group, 'Import Root Anchor', 'synthetic', 'synthetic')
    child = remote.add_group(remote.root_group, 'Import Subgroup')
    remote.add_entry(child, 'Import Child Anchor', 'synthetic', 'synthetic')
    remote.save()

    for stem, keep in (('export-edit', True), ('export-flat', False)):
        db = parent(outdir / (stem + '-parent.kdbx'))
        target = group(db, 'Team Sync')
        export_reference(target, stem + '-output.kdbx', keep)
        db.add_entry(target, stem + ' Root Entry', 'synthetic', 'synthetic')
        child = db.add_group(target, stem + ' Populated Subgroup')
        db.add_entry(child, stem + ' Child Entry', 'synthetic', 'synthetic')
        put_custom(target, 'KP2A/KeeShare/fixture-marker', 'must-strip-root')
        put_custom(target, 'unrelated-final-marker', 'preserve-root')
        put_custom(child, 'KeeShare/Reference', 'synthetic-invalid-reference')
        put_custom(child, 'KP2A/KeeShare/fixture-marker', 'must-strip-child')
        put_custom(child, 'unrelated-final-marker', 'preserve-child')
        db.save()

    db = parent(outdir / 'empty-parent.kdbx')
    set_reference(group(db, 'Team Import'), '')
    db.add_entry(group(db, 'Team Import'), 'Empty Path Preserved', 'synthetic', 'synthetic')
    inactive = db.add_group(db.root_group, 'Inactive Control')
    set_reference(inactive, '')
    item = inactive._element.find('CustomData/Item/Value')
    xml = etree.fromstring(base64.b64decode(item.text))
    for direction in list(xml.find('Type')):
        xml.find('Type').remove(direction)
    item.text = base64.b64encode(etree.tostring(xml)).decode()
    db.add_entry(inactive, 'Inactive Preserved', 'synthetic', 'synthetic')
    db.save()
    picked = create_database(outdir / 'picked-share.kdbx', password='share-pass')
    picked.add_entry(picked.root_group, MARKER, 'synthetic', 'synthetic')
    picked.save()
    for name in ('move-parent', 'export-edit-parent', 'export-flat-parent', 'empty-parent'):
        db = database(outdir / (name + '.kdbx'))
        assert not any(key.startswith(IOC_PREFIX) for g in db.groups for key in custom(g)), \
            'Input must not preseed a current-device IOC'
    return {'inputs': sorted(path.name for path in outdir.iterdir()),
            'picker_marker': MARKER, 'current_device_ioc_preseeded': False}


# These are the exact missing/default fields observed when KeePassLib saved the
# pykeepass fixture. Preserve every other field, including modification/location
# timestamps; navigation access counters are checked separately below.
SERIALIZER_DEFAULTS = {
    'Group': {'Notes': '', 'IconID': '48', 'IsExpanded': 'True',
              'DefaultAutoTypeSequence': '', 'EnableAutoType': 'null',
              'EnableSearching': 'null', 'LastTopVisibleEntry': 'AAAAAAAAAAAAAAAAAAAAAA=='},
    'Entry': {'IconID': '0', 'ForegroundColor': '', 'BackgroundColor': '',
              'OverrideURL': '', 'Tags': '', 'History': ''},
    'AutoType': {'DefaultSequence': ''},
}


def logical_element(element, db):
    """Compare decoded XML fields, explicit serializer defaults and child order."""
    node = deepcopy(element)
    for times in node.iter('Times'):
        for field in times:
            if field.tag.endswith('Time') or field.tag == 'LocationChanged':
                field.text = db._decode_time(field.text).isoformat()
    def canonical(item):
        defaults = SERIALIZER_DEFAULTS.get(item.tag, {})
        children = [child for child in item if not (
            child.tag in defaults and len(child) == 0 and not child.attrib and
            (child.text or '') == defaults[child.tag])]
        # XML field ordering differs between serializers. Preserve ordered lists
        # (groups, entries, history, association, binaries) rather than sorting them.
        ordered = [canonical(child) for child in children if child.tag in
                   ('Group', 'Entry', 'Association', 'Binary')]
        fields = sorted((canonical(child) for child in children if child.tag not in
                         ('Group', 'Entry', 'Association', 'Binary')), key=repr)
        return (item.tag, tuple(sorted(item.attrib.items())), item.text or '', tuple(fields), tuple(ordered))
    return repr(canonical(node))


def tree(db, root=None, omit_entry_uuid=None, accessed_group_uuids=()):
    node = deepcopy((root if root is not None else db.root_group)._element)
    if omit_entry_uuid:
        for entry in list(node.iter('Entry')):
            if entry.findtext('UUID') == omit_entry_uuid:
                entry.getparent().remove(entry)
    for target in node.iter('Group'):
        if target.findtext('UUID') in accessed_group_uuids:
            for tag in ('LastAccessTime', 'UsageCount'):
                field = target.find('Times/' + tag)
                target.find('Times').remove(field)
    return logical_element(node, db)


def assert_source_edit_unchanged(before, after, entry_uuid):
    """Allow one saved entry and exactly observed ordinary group-access updates."""
    entry = before.find_entries(uuid=entry_uuid, first=True)
    changed = after.find_entries(uuid=entry_uuid, first=True)
    assert changed is not None and changed.parentgroup.uuid == entry.parentgroup.uuid
    accessed = []
    differences = []
    for original in (before.root_group, entry.parentgroup):
        actual = after.find_groups(uuid=original.uuid, first=True)
        assert actual is not None
        a = original._element.find('Times')
        b = actual._element.find('Times')
        old_usage, new_usage = int(a.findtext('UsageCount')), int(b.findtext('UsageCount'))
        old_access = before._decode_time(a.findtext('LastAccessTime'))
        new_access = after._decode_time(b.findtext('LastAccessTime'))
        assert new_usage == old_usage + 1, 'Unexpected navigation usage count'
        assert new_access >= old_access, 'Navigation access timestamp went backward'
        accessed.append(original._element.findtext('UUID'))
        differences.append({'uuid': str(original.uuid), 'name': original.name,
            'LastAccessTime': [old_access.isoformat(), new_access.isoformat()],
            'UsageCount': [old_usage, new_usage]})
    omit = entry._element.findtext('UUID')
    assert tree(before, omit_entry_uuid=omit, accessed_group_uuids=accessed) == \
        tree(after, omit_entry_uuid=omit, accessed_group_uuids=accessed), \
        'Source content/hierarchy/metadata changed outside edited entry and exact access counters'
    return differences


def assert_no_sharing(db):
    for target in db.groups:
        assert not any(key == 'KeeShare/Reference' or key.startswith('KP2A/KeeShare/')
                       for key in custom(target)), 'Sharing metadata leaked into export'
