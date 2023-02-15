import asyncio
import datasette
from datasette.utils import await_me_maybe
import markupsafe
from .hookspecs import hookimpl
import datetime
import re
import json
from .utils import row_edit_params, is_row_page
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


@hookimpl(trylast=True, specname='edit_control')
def string_control(datasette, database, table, column):
    return 'StringAutocompleteControl'
    #return 'StringControl'

def number_control(datasette, database, table, column, row, value, metadata):
    type = metadata['type']
    if type.lower() in numeric_types:
        return 'NumberControl'

def boolean_control(datasette, database, table, column, row, value, metadata):
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

def date_control(datasette, database, table, column, row, value, metadata):
    # Use cases:
    # 1. type == DATE and no data: DATE
    # 2. strings that looks like date: DATE
    # 3. stringy and looks like a timestamp: whatever
    # 4. timestamptz and no data - store as ISO8601 with millis precision


    format = infer_format(metadata)

    if format:
        return 'DateControl', format

def foreign_key_control(datasette, database, table, column, row, value, metadata):
    async def inner():
        db = datasette.databases[database]
        # Is this column an fkey?
        fkeys = list(await db.execute('SELECT "table", "to" FROM pragma_foreign_key_list(?) WHERE "from" = ?', [table, column]))

        # We don't support compound foreign keys.
        if len(fkeys) == 1:
            other_table, other_column = fkeys[0]
            label_column = await db.label_column_for_table(other_table)
            the_other_row = list(await db.execute('SELECT "{}" FROM "{}" WHERE "{}" = ?'.format(label_column, other_table, other_column), [value]))
            return 'ForeignKeyControl', {
                'other_autosuggest_column_url': '{}/-/dux-autosuggest-column'.format(datasette.urls.table(database, other_table)),
                'other_table': other_table,
                'other_column': other_column,
                'label_column': label_column,
                'initial_label': the_other_row[0][0] if the_other_row else None
            }

    return inner

def textarea_control(datasette, database, table, column, row, value, metadata):
    if 'texts_newline' in metadata and metadata['texts_newline']:
        return 'TextareaControl'

def dropdown_control(datasette, database, table, column, row, value, metadata):
    if not 'check_choices' in metadata:
        return

    return 'DropdownControl', { 'choices': [{ 'value': x, 'label': x } for x in metadata['check_choices']] }

def json_tags_control(datasette, database, table, column, row, value, metadata):
    if 'json_arrays' in metadata and metadata['json_arrays'] + metadata['nulls'] == metadata['count']:
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

# Conceptually, it'd be nice if we just added hooks with relative priorities,
# but pluggy doesn't permit explicit priorities beyond tryfirst/trylast.
#
# Add hooks here in decreasing order of specificity
explicit_hook_order = [
    json_tags_control,
    dropdown_control,
    foreign_key_control,
    date_control,
    textarea_control,
    boolean_control,
    number_control,
    # string_control, # string_control is a trylast, so we ignore it
]

@hookimpl(specname='edit_control')
def meta_edit_control(datasette, database, table, column, row, value, metadata):
    async def inner():
        for hook in explicit_hook_order:
            rv = await await_me_maybe(hook(datasette, database, table, column, row, value, metadata))

            if rv:
                return rv

    return inner


@datasette.hookimpl(tryfirst=True, specname='render_cell')
def render_cell_edit_control(datasette, database, table, column, row, value):
    async def inner():
        task = asyncio.current_task()
        request = None if not hasattr(task, '_duxui_request') else task._duxui_request

        if not is_row_page(request):
            return

        params = await row_edit_params(datasette, request, database, table)
        if params and column in params:
            db = datasette.get_database(database)

            data = params[column]

            default_value = data['default_value']
            default_value_value = None

            if default_value:
                default_value_value = list(await db.execute("SELECT {}".format(default_value)))[0][0]

            controls = pm.hook.edit_control(datasette=datasette, database=database, table=table, column=column, row=row, value=value, metadata=data)
            control = None
            for maybe in controls:
                control = await await_me_maybe(maybe)
                if control:
                    break

            if control:
                config = {}

                if isinstance(control, tuple):
                    for k, v in control[1].items():
                        config[to_camel_case(k)] = v
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

@hookimpl(trylast=True)
def redirect_after_edit(datasette, database, table, action, pk):
    if action == 'delete-row':
        return datasette.urls.table(database, table)
    return '{}/{}'.format(datasette.urls.table(database, table), pk)
