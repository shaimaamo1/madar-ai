import argparse
import sqlite3
import tempfile
from pathlib import Path

from backend import db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.resolve() == db.DB_PATH.resolve() or args.output.exists():
        parser.error('Use a new backup path outside the active database')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db.DB_PATH) as source, sqlite3.connect(args.output) as target:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    args.output.chmod(0o600)
    with tempfile.TemporaryDirectory(prefix='madar-restore-') as directory:
        with sqlite3.connect(args.output) as source, sqlite3.connect(Path(directory) / 'restore.sqlite3') as restored:
            source.backup(restored)
            assert restored.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            original = source.execute('SELECT COUNT(*) FROM tenants').fetchone()[0]
            assert restored.execute('SELECT COUNT(*) FROM tenants').fetchone()[0] == original
    print('Consistent database backup created; integrity and isolated restore verified.')


if __name__ == '__main__':
    main()
