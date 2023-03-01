import sqlite3
import pytest

from datasette_ui_extras.dux_command import dux_the_file

def test_compute_column_stats(tmp_path):
    db_name = tmp_path / "db.sqlite"
    conn = sqlite3.connect(db_name)
    with conn:
        conn.execute("CREATE TABLE data(id integer primary key, title text, json text, age integer, blobby blob, ratio real)")
        conn.execute("INSERT INTO data(id, title, json, age, ratio) VALUES (1, 'title1', '[\"foo\"]', X'35', 0.43)").fetchall()
        conn.execute("INSERT INTO data(id, title, json) VALUES (2, 'title2', 'not json')").fetchall()
    conn.close()

    dux_the_file(db_name)

    conn = sqlite3.connect(db_name)
    with conn:
        # Confirm that our triggers are OK with a blob.
        conn.execute("INSERT INTO data(id, title, json, blobby, ratio) VALUES (3, 'title1', '[\"foo\"]', X'39', 0.43)").fetchall()
    conn.close()

    # Confirm that we can drain the queue of pending rows
    dux_the_file(db_name)

