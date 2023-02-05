from .hookspecs import hookimpl

@hookimpl
def edit_control(datasette, database, table, column):
    return 'StringControl'
