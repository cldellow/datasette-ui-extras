from datasette.app import Datasette
import pytest
import json
import sqlite3


@pytest.mark.asyncio
async def test_plugin_is_installed():
    datasette = Datasette(memory=True)
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-ui-extras" in installed_plugins

@pytest.mark.asyncio
async def test_updatable_view(tmp_path):
    db_name = tmp_path / "db.sqlite"
    conn = sqlite3.connect(db_name)
    with conn:
        conn.execute("CREATE TABLE data(id integer primary key, title text, other text)")
        conn.execute("INSERT INTO data(id, title) VALUES (1, 'title1')").fetchall()
        conn.execute("INSERT INTO data(id, title) VALUES (2, 'title2')").fetchall()
        conn.execute("CREATE VIEW view AS SELECT id, 'some jazz' as instructions, title, other as uneditable FROM data")
        conn.execute("""
CREATE TRIGGER update_underlying_fields INSTEAD OF UPDATE OF title ON view
BEGIN
   UPDATE data SET title = new.title WHERE id = old.id;
END;
""")
    conn.close()

    datasette = Datasette(
        memory=True,
        plugins_dir='./tests/plugins/',
        files=[db_name]
    )

    response = await datasette.client.get("/db.json")
    assert response.status_code == 200

    response = await datasette.client.get("/db/data.json")
    assert response.status_code == 200

    response = await datasette.client.get("/db/data/1.json?_shape=array")
    assert response.status_code == 200
    assert response.json() == [{'id': 1, 'title': 'title1', 'other': None}]

    response = await datasette.client.get("/db/view/1.json?_shape=array")
    assert response.status_code == 200
    assert response.json() == [{'id': 1, 'instructions': 'some jazz', 'uneditable': None, 'title': 'title1'}]

    response = await datasette.client.post(
        "/db/view/1/-/update",
        headers={
            'content-type': 'application/json',
        },
        content=json.dumps({
            "update": {
                "title": "new title",
            }
        })
    )
    assert response.status_code == 200

    response = await datasette.client.get("/db/view/1.json?_shape=array&_col=title")
    assert response.status_code == 200
    assert response.json() == [{'id': 1, 'instructions': 'some jazz', 'uneditable': None, 'title': 'new title'}]

    response = await datasette.client.get("/db/view/1")
    assert response.status_code == 200


# Test cases to add
# - ?_edit_dux=1 when you lack update-row should 403
# - ?_edit_dux=1 when you have update-row should 200
