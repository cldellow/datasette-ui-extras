from .hookspecs import hookimpl

# From https://www.sqlite.org/datatype3.html#affinity_name_examples
numeric_types = [
    'int',
    'integer',
    'tinyint',
    'smallint',
    'mediumint',
    'bigint',
    'int2',
    'int8',
    'real',
    'double',
    'double precision',
    'float',
]

@hookimpl(specname='edit_control')
def number_control(type):
    print(type)
    if type.lower() in numeric_types:
        return 'NumberControl'

@hookimpl(trylast=True, specname='edit_control')
def string_control(datasette, database, table, column):
    return 'StringControl'
