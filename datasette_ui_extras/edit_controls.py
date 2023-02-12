import asyncio
import datasette
import markupsafe
from .hookspecs import hookimpl
import datetime
import re
import json
from .utils import row_edit_params
from .plugin import pm

re_iso8601_date = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
re_iso8601_millis = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ])[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]+Z?$')
re_iso8601_secs = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ])[0-9]{2}:[0-9]{2}:[0-9]{2}Z?$')

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

def is_iso8601_date(x):
    return re_iso8601_date.search(x)

def infer_format(metadata):
    if not 'min' in metadata or not 'max' in metadata:
        if metadata['type'].lower() == 'date':
            return {
                'precision': 'date',
                'utc': False
            }

        return

    min = metadata['min']
    max = metadata['max']

    # Maybe in the future we can support seconds since the epoch / julian days,
    # for now only ISO8601.
    if not isinstance(min, str) or not isinstance(max, str):
        return

    if re_iso8601_date.search(min) and re_iso8601_date.search(max):
        return {
            'precision': 'date',
            'utc': False,
        }

    min_z = min.endswith('Z')
    max_z = max.endswith('Z')
    min_t = 'T' in min
    max_t = 'T' in max

    min_millis = re_iso8601_millis.search(min)
    max_millis = re_iso8601_millis.search(max)

    if min_millis and max_millis and min_z == max_z and min_t == max_t:
        return {
            'precision': 'millis',
            'utc': min_z,
            't': min_t
        }

    min_secs = re_iso8601_secs.search(min)
    max_secs = re_iso8601_secs.search(max)

    if min_secs and max_secs and min_z == max_z and min_t == max_t:
        return {
            'precision': 'secs',
            'utc': min_z,
            't': min_t
        }

@hookimpl(specname='edit_control')
def date_control(metadata, value):
    # Use cases:
    # 1. type == DATE and no data: DATE
    # 2. strings that looks like date: DATE
    # 3. stringy and looks like a timestamp: whatever
    # 4. timestamptz and no data - store as ISO8601 with millis precision


    format = infer_format(metadata)

    if format:
        return 'DateControl', format

@hookimpl(specname='edit_control')
def textarea_control(metadata):
    if 'texts_newline' in metadata and metadata['texts_newline']:
        return 'TextareaControl'

@hookimpl(specname='edit_control')
def dropdown_control(metadata):
    if not 'check_choices' in metadata:
        return

    return 'DropdownControl', { 'choices': [{ 'value': x, 'label': x } for x in metadata['check_choices']] }

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
def render_cell_edit_control(datasette, database, table, column, row, value):
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
            control = pm.hook.edit_control(datasette=datasette, database=database, table=table, column=column, row=row, value=value, metadata=data)
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
