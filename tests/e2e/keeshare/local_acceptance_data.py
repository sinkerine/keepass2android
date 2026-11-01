"""Synthetic inputs and persisted-output oracles for local acceptance gaps."""
from pykeepass import PyKeePass, create_database
from make_fixtures import make_fixtures, set_reference
from journey_data import custom, put_custom, group_state

FOREIGN_KEY = 'KP2A/KeeShare/Ioc/synthetic-foreign-device-local-acceptance'
PREFIX = 'KP2A/KeeShare/Ioc/'


def database(path):
    return PyKeePass(path, password='main-pass')


def group(db, name):
    result = db.find_groups(name=name, first=True)
    assert result is not None, 'Missing persisted group: ' + name
    return result


def state(db, name):
    root = group(db, name)
    groups = group_state(root)
    return {'groups': groups, 'entries': {
        str(entry.uuid): {'title': entry.title, 'username': entry.username,
                          'password': entry.password, 'parent': str(entry.parentgroup.uuid),
                          'ctime': entry.ctime.isoformat(), 'mtime': entry.mtime.isoformat()}
        for entry in db.entries if str(entry.parentgroup.uuid) in groups}}


def prepare(outdir, canonical_files):
    make_fixtures(outdir)
    db = database(outdir / 'main.kdbx')
    imported = group(db, 'Team Import')
    # A valid serialized local IOC, under a deliberately different device key.
    put_custom(imported, FOREIGN_KEY, '|' + canonical_files + '/bad.kdbx|N||')
    db.save()
    remote = PyKeePass(outdir / 'team-import.kdbx', password='share-pass')
    child = remote.add_group(remote.root_group, 'Imported Nested')
    remote.add_entry(child, 'Nested Readonly Entry', 'synthetic', 'synthetic')
    remote.save()
    (outdir / 'bad.kdbx').write_bytes(b'Synthetic corrupt local acceptance container\n')

    missing = create_database(outdir / 'missing.kdbx', password='main-pass')
    for name, path in [('Team Import', ''), ('Unresolved Location', 'C:\\unmapped\\share.kdbx')]:
        target = missing.add_group(missing.root_group, name)
        set_reference(target, path)
        missing.add_entry(target, name + ' Preserved', 'synthetic', 'synthetic')
    missing.add_group(missing.root_group, 'Team Sync')
    missing.add_group(missing.root_group, 'Personal')
    missing.save()

    continuation = create_database(outdir / 'continuation.kdbx', password='main-pass')
    failed = continuation.add_group(continuation.root_group, 'Team Import')
    set_reference(failed, 'bad.kdbx')
    continuation.add_entry(failed, 'Failed Share Preserved', 'synthetic', 'synthetic')
    successful = continuation.add_group(continuation.root_group, 'Team Sync')
    set_reference(successful, 'continuation-share.kdbx', synchronize=True)
    continuation.add_group(continuation.root_group, 'Personal')
    continuation.save()
    share = create_database(outdir / 'continuation-share.kdbx', password='share-pass')
    share.add_entry(share.root_group, 'Later Share Success Marker', 'synthetic', 'synthetic')
    share.save()
    return {'foreign_key': FOREIGN_KEY,
            'share_order': [str(failed.uuid), str(successful.uuid)],
            'missing_sha_input': str(outdir / 'missing.kdbx')}
