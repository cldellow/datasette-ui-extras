from datasette import hookimpl
import click
import sqlite3
import sqlite_sqlean
import json
import os
from .column_stats_schema import ensure_schema_and_triggers
from .column_stats import ensure_empty_rows_for_db, index_next_backfill_batch, index_pending_rows

@hookimpl
def prepare_connection(conn):
    conn.enable_load_extension(True)
    sqlite_sqlean.load(conn, 'crypto')
    conn.enable_load_extension(False)

    # Try to enable WAL and synchronous = NORMAL mode
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA synchronous = NORMAL')

    # Foreign keys are great, databases should enforce them.
    conn.execute('PRAGMA foreign_keys = ON')

@hookimpl(specname='register_commands')
def dux_command(cli):
    @cli.command()
    @click.argument(
        "files", type=click.Path(exists=True), nargs=-1
    )
    def dux(files):
        "Add datasette-ui-extras's triggers and stats tables to the given database(s)."

        for file in files:
            conn = sqlite3.connect(str(file))
            conn.row_factory = sqlite3.Row
            prepare_connection(conn)

            ensure_schema_and_triggers(conn)
            ensure_empty_rows_for_db(conn)

            while index_next_backfill_batch(conn):
                pass

            while index_pending_rows(conn):
                pass

            conn.close()
