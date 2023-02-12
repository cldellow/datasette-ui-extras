import sqlite3
import pytest

def test_compute_column_stats(tmp_path):
    # TODO: re-write this test to be compatible with the new indexing system
    if False:
        conn = sqlite3.connect(db_name)
        with conn:
            conn.execute("CREATE TABLE data(id integer primary key, title text, json text, age integer, blobby blob, ratio real)")
            conn.execute("INSERT INTO data(id, title, json, age, ratio) VALUES (1, 'title1', '[\"foo\"]', 23, 0.43)").fetchall()
            conn.execute("INSERT INTO data(id, title, json) VALUES (2, 'title2', 'not json')").fetchall()

        conn.row_factory = sqlite3.Row
        limit = 1000
        distinct_limit = 100
        rv = compute_column_stats(conn, 'data', 'json', limit, distinct_limit)
