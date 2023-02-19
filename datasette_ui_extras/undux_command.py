from datasette import hookimpl
import click
import sqlite3
import json
import os

@hookimpl(specname='register_commands')
def undux_command(cli):
    @cli.command()
    @click.argument(
        "files", type=click.Path(exists=True), nargs=-1
    )
    def undux(files):
        "Remove datasette-ui-extras's triggers and stats tables from the given database(s)."

        for file in files:
            conn = sqlite3.connect(str(file))

            for trigger, in list(conn.execute("select name from sqlite_master where name like 'dux_%' and type = 'trigger'")):
                conn.execute('DROP TRIGGER "{}"'.format(trigger))

            for table, in list(conn.execute("select name from sqlite_master where name like 'dux_%' and type = 'table'")):
                conn.execute('DROP TABLE "{}"'.format(table))
