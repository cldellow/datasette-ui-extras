import pytest

from datasette_ui_extras.yolo_command import enable_yolo_for_metadata

def test_enable_yolo_for_metadata_empty():
    rv = enable_yolo_for_metadata({}, 'somedb')
    assert rv == {
        'databases': {
            'somedb': {
                'permissions': {
                    'create-table': True,
                    'drop-table': True,
                    'insert-row': True,
                    'update-row': True,
                    'delete-row': True,
                }
            }
        }
    }
 
def test_enable_yolo_for_metadata_existing():
    rv = enable_yolo_for_metadata({
        'databases': {
            'somedb': {
                'other': True
            }
        }
    }, 'somedb')
    assert rv == {
        'databases': {
            'somedb': {
                'other': True,
                'permissions': {
                    'create-table': True,
                    'drop-table': True,
                    'insert-row': True,
                    'update-row': True,
                    'delete-row': True,
                }
            }
        }
    }
 
