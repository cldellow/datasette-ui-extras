from datasette import hookimpl
import click
import sqlite3
import json
import os

@hookimpl(specname='register_commands')
def yolo_command(cli):
    @cli.command()
    @click.argument(
        "files", type=click.Path(), nargs=-1
    )
    def yolo(files):
        "Enable very permissive access to the specified databases."

        # First, enable WAL mode for all the databases, creating them
        # if needed.
        for file in files:
            conn = sqlite3.connect(str(file))
            try:
                conn.execute('PRAGMA journal_mode = WAL')
            except sqlite3.DatabaseError:
                raise click.ClickException(
                    "Invalid database: {}".format(file)
                )

        # Second, ensure there is a metadata.json that is permissive
        metadata = {}
        indent = 4
        try:
            f = open('metadata.json', 'r')
            raw_json = f.read()
            metadata = json.loads(raw_json)
            if not '    ' in raw_json:
                indent = 2
            f.close()
        except FileNotFoundError:
            pass

        for file in files:
            db = os.path.basename(file)
            if '.' in db:
                db = '.'.join(db.split('.')[0:-1])
            metadata = enable_yolo_for_metadata(metadata, db)


        f = open('metadata.json', 'w')
        f.write(json.dumps(metadata, indent=indent))
        f.close()

def enable_yolo_for_metadata(metadata, db):
    rv = json.loads(json.dumps(metadata))

    if not 'databases' in rv:
        rv['databases'] = {}

    if not db in rv['databases']:
        rv['databases'][db] = {}

    if not 'permissions' in rv['databases'][db]:
        rv['databases'][db]['permissions'] = {}

    for perm in ['create-table', 'drop-table', 'insert-row', 'update-row', 'delete-row']:
        rv['databases'][db]['permissions'][perm] = True

    return rv
