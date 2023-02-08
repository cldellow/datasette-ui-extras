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

# In general, hooks higher in this file run after hooks lower than
# them.

@hookimpl(trylast=True, specname='edit_control')
def string_control(datasette, database, table, column):
    return 'StringAutocompleteControl'
    #return 'StringControl'

@hookimpl(specname='edit_control')
def number_control(metadata):
    type = metadata['type']
    if type.lower() in numeric_types:
        return 'NumberControl'

@hookimpl(specname='edit_control')
def textarea_control(metadata):
    if 'texts_newline' in metadata and metadata['texts_newline']:
        return 'TextareaControl'


