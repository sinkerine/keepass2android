"""Additional synthetic fixtures and independent persisted-output assertions for T8.

KeeShare behavior itself runs only in the installed Android app.
"""
import base64
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED, is_zipfile

from lxml import etree
from pykeepass import PyKeePass


def custom(group):
    return {item.findtext('Key'): item.findtext('Value')
            for item in group._element.findall('CustomData/Item')}


def put_custom(group, key, value):
    node = group._element.find('CustomData')
    if node is None:
        node = etree.SubElement(group._element, 'CustomData')
    item = etree.SubElement(node, 'Item')
    etree.SubElement(item, 'Key').text = key
    etree.SubElement(item, 'Value').text = value


def inactive_reference(group):
    xml = ('<KeeShare><Type/><Group>' + base64.b64encode(group.uuid.bytes).decode()
           + '</Group><Path>bmVzdGVkLmtkYng=</Path><Password/>'
           + '<KeepGroups>True</KeepGroups></KeeShare>')
    return base64.b64encode(xml.encode()).decode()


def load_share(path):
    if is_zipfile(path):
        with ZipFile(path) as archive:
            assert archive.namelist() == ['container.share.kdbx']
            return PyKeePass(BytesIO(archive.read('container.share.kdbx')), password='share-pass')
    return PyKeePass(path, password='share-pass')


def save_zip(db, path):
    data = BytesIO()
    db.save(data)
    with ZipFile(path, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('container.share.kdbx', data.getvalue())


def enrich(outdir):
    main = PyKeePass(outdir / 'main.kdbx', password='main-pass')
    personal = main.find_groups(name='Personal', first=True)
    child = main.add_group(personal, 'Personal Nested')
    main.add_entry(child, 'Nested Personal Entry', 'synthetic', 'synthetic')
    grandchild = main.add_group(child, 'Personal Deep')
    for group in (personal, child, grandchild):
        put_custom(group, 'unrelated-fixture-key', 'preserve-me')
        put_custom(group, 'KP2A/KeeShare/Ioc/synthetic-other-device', 'synthetic-not-an-ioc')
        put_custom(group, 'KP2A/KeeShare/fixture-marker', 'local-marker')
    # Malformed remote/local metadata must also be stripped on export, without
    # adding extra configured-share rows to the core UI journey.
    put_custom(child, 'KeeShare/Reference', 'synthetic-invalid-reference')
    put_custom(grandchild, 'KeeShare/Reference', 'synthetic-invalid-reference')

    sync = main.find_groups(name='Team Sync', first=True)
    local = main.add_group(sync, 'Z Configured Nested')
    put_custom(local, 'KeeShare/Reference', inactive_reference(local))
    put_custom(local, 'KP2A/KeeShare/Ioc/synthetic-other-device', 'local-nested-device-value')
    put_custom(local, 'KP2A/KeeShare/fixture-marker', 'local-nested-marker')
    put_custom(local, 'unrelated-fixture-key', 'local-nested-unrelated')
    main.save()
    path = outdir / 'team-sync.kdbx.share'
    remote = load_share(path)
    matching = remote.add_group(remote.root_group, 'Z Configured Nested')
    matching.uuid = local.uuid
    matching.ctime = local.ctime
    remote.add_entry(matching, 'Nested Remote Entry', 'synthetic', 'synthetic')
    save_zip(remote, path)


def group_state(group):
    """Persisted group times/usage and all custom data keyed by stable UUID."""
    def descendants(parent):
        yield parent
        for child in parent.subgroups:
            yield from descendants(child)
    groups = list(descendants(group))
    result = {}
    for item in groups:
        result[str(item.uuid)] = {
            'name': item.name,
            'times': {field.tag: (item._kp._decode_time(field.text).isoformat()
                                  if field.tag.endswith('Time') or field.tag == 'LocationChanged'
                                  else field.text)
                      for field in item._element.find('Times')},
            'custom': custom(item),
            'parent': str(item.parentgroup.uuid) if item is not group else None,
        }
    return result


def assert_sanitized(source_group, exported):
    source = group_state(source_group)
    output = group_state(exported.root_group)
    assert source.keys() == output.keys(), 'Exported group membership differs'
    for uuid, state in source.items():
        actual = output[uuid]
        assert actual['times'] == state['times'], 'Export changed group timestamps/usage: ' + state['name']
        expected = {k: v for k, v in state['custom'].items()
                    if k != 'KeeShare/Reference' and not k.startswith('KP2A/KeeShare/')}
        assert actual['custom'] == expected, 'Export metadata differs: ' + state['name']
        assert actual['parent'] == state['parent'], 'Export hierarchy differs'
