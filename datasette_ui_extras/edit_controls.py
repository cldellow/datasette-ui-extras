from .hookspecs import hookimpl
import json

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

@hookimpl(specname='edit_control')
def dropdown_control(metadata):
    if not 'choices' in metadata:
        return

    return 'DropdownControl', { 'choices': metadata['choices'] }

@hookimpl(specname='edit_control')
def json_tags_control(metadata):
    if 'jsons' in metadata and metadata['jsons'] + metadata['nulls'] == metadata['count']:
        try:
            min_parsed = json.loads(metadata['min'])
            max_parsed = json.loads(metadata['max'])

            if not isinstance(min_parsed, list) or not isinstance(max_parsed, list):
                return

            if min_parsed and not isinstance(min_parsed[0], str):
                return

            if max_parsed and not isinstance(max_parsed[0], str):
                return

            return 'JSONTagsControl'
        except:
            return

