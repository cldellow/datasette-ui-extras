import asyncio
import datasette
import markupsafe
from .hookspecs import hookimpl
import json
from .utils import row_edit_params
from .plugin import pm

def to_camel_case(snake_str):
    # from https://stackoverflow.com/a/19053800
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

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
def boolean_control(metadata):
    type = metadata['type']

    is_boolean = type.lower() == 'boolean'
    is_booleanish = 'min' in metadata and 'max' in metadata and isinstance(metadata['min'], int) and isinstance(metadata['max'], int) and metadata['min'] >= 0 and metadata['max'] <= 1

    if not is_boolean and not is_booleanish:
        return

    if not metadata['nullable']:
        return 'CheckboxControl'

    if type.lower() in numeric_types or type.lower() == 'boolean':
        return 'DropdownControl', { 'choices': [
            { 'value': 0, 'label': 'False' },
            { 'value': 1, 'label': 'True' },
        ]}

    return 'DropdownControl', { 'choices': [
        { 'value': '0', 'label': 'False' },
        { 'value': '1', 'label': 'True' },
    ]}


@hookimpl(specname='edit_control')
def textarea_control(metadata):
    if 'texts_newline' in metadata and metadata['texts_newline']:
        return 'TextareaControl'

@hookimpl(specname='edit_control')
def dropdown_control(metadata):
    if not 'choices' in metadata:
        return

    return 'DropdownControl', { 'choices': [{ 'value': x, 'label': x } for x in metadata['choices']] }

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

@datasette.hookimpl(tryfirst=True, specname='render_cell')
def render_cell_edit_control(datasette, database, table, column, value):
    async def inner():
        task = asyncio.current_task()
        request = None if not hasattr(task, '_duxui_request') else task._duxui_request

        params = await row_edit_params(datasette, request, database, table)
        if params and column in params:
            db = datasette.get_database(database)

            data = params[column]

            default_value = data['default_value']
            default_value_value = None

            if default_value:
                default_value_value = list(await db.execute("SELECT {}".format(default_value)))[0][0]
            control = pm.hook.edit_control(datasette=datasette, database=database, table=table, column=column, metadata=data)
            if control:
                config = {}

                if isinstance(control, tuple):
                    for k, v in control[1].items():
                        config[k] = v
                    control = control[0]

                for k, v in data.items():
                    if k == 'name':
                        k = 'column'
                    config[to_camel_case(k)] = v

                if 'base_table' in data:
                    base_table = data['base_table']
                    config['autosuggestColumnUrl'] = '{}/-/dux-autosuggest-column'.format(datasette.urls.table(database, base_table))

                config['database'] = database
                config['tableOrView'] = table

                return markupsafe.Markup(
                    '<div class="dux-edit-stub" data-control="{control}" data-initial-value="{value}" data-config="{config}">Loading...</div>'.format(
                        control=markupsafe.escape(control),
                        value=markupsafe.escape(json.dumps(value)),
                        config=markupsafe.escape(json.dumps(config)),
                    )
                )

    return inner
