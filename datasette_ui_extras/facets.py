import time
import re
import json
from datasette import facets
from datasette.facets import load_facet_configs
from datasette.utils import path_with_added_args
from .facet_patches import ArrayFacet_facet_results

likely_date_re = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}')

async def no_suggest(self):
    return []

async def no_facet_results(self):
    return [], []

# Disable facets in non-JSON contexts
def json_only(underlying):
    async def rv(self):
        # We should actually parse the URL, but eh, good enough.
        is_json = '.json' in self.request.url

        if is_json:
            return await underlying(self)

        return await no_facet_results(self)

    return rv

def facet_from_qs(args):
    key = args.get('_dux_facet')
    value = args.get('_dux_facet_column')

    if key == '_facet':
        return { 'simple': value }
    elif key.startswith("_facet_"):
        type = key[len("_facet_") :]
        rv = {}
        # TODO: see issue #31
        rv['simple'] = value
        return rv

Facet_get_configs = facets.Facet.get_configs
def patched_get_configs(self):
    rv = Facet_get_configs(self)

    # There will be exactly 1 facet query string parameter, like
    # _facet=xxx, _facet_date=xxx, _facet_array=xxx

    from_qs = facet_from_qs(self.request.args)

    if not from_qs:
        # This is unexpected, maybe we ought to throw?
        return []

    # If it's in metadata, it'll show up twice -- once from metadata,
    # and once from our JS code explicitly asking for it in the qs.
    # Just take the metadata one.
    new_rv = [x for x in rv if x['config'] == from_qs][0:1]
    return new_rv


def patch_TableView_data():
    from datasette.views.table import TableView

    original_data = TableView.data
    async def patched_data(
        self,
        request,
        default_labels=False,
        _next=None,
        _size=None,
    ):
        rv = await original_data(self, request, default_labels, _next, _size)

        if not isinstance(rv, tuple):
            return rv

        rows = rv[0]['rows']
        extra_template_fn = rv[1]

        extra_template = await extra_template_fn()
        request = extra_template['request']

        async def cached_extra_template():
            return extra_template

        request._dux_rows = rows

        # Replace the extra_template fn call with one that uses the value
        # we just computed
        rv = (rv[0], cached_extra_template, rv[2])
        return rv
    TableView.data = patched_data

def enable_yolo_facets():
    # Monkey patch a bunch of things to enable an alternative facet experience.

    # Only compute facets for requests with _dux_facet and _dux_facet_column
    facets.Facet.get_configs = patched_get_configs

    # TODO: is there a clean way we can patch these on demand?
    # Can we just enumerate pm.hook.register_facet_classes?
    from datasette.plugins import pm
    targets = [y for x in pm.hook.register_facet_classes() for y in x]

    for target in targets:
        # Suppress facet suggestion
        target.suggest = no_suggest

        # Only compute facet results on JSON API calls
        target.facet_results = json_only(target.facet_results)

    # We'd like to smuggle info about the current page's rows to our extra_body_script
    # handler.
    patch_TableView_data()

def facets_extra_body_script(template, database, table, columns, view_name, request, datasette):
    if view_name != 'table':
        return

    scripts = []

    scripts.append(get_extra_body_script_for_dux_facets(template, database, table, columns, view_name, request, datasette))

    scripts.append(get_extra_body_script_for_dux_facet_suggestions(template, database, table, columns, view_name, request, datasette))
    return '''
{}
'''.format('\n'.join([script for script in scripts if script]))

def get_extra_body_script_for_dux_facet_suggestions(template, database, table, columns, view_name, request, datasette):
    if not request._dux_rows:
        return ''

    num_rows = len(request._dux_rows)

    num_columns = len(columns)

    nulls = [0] * num_columns
    strs = [0] * num_columns
    ints = [0] * num_columns
    floats = [0] * num_columns
    dates = [0] * num_columns
    json_str_arrays = [0] * num_columns

    for row in request._dux_rows:
        for i, name in enumerate(columns):
            value = row[name]

            if value == None:
                nulls[i] += 1
            if isinstance(value, str):
                strs[i] += 1

                if (value.startswith('["') and value.endswith('"]')) or value == '[]':
                    json_str_arrays[i] += 1

                if likely_date_re.search(value):
                    dates[i] += 1
            if isinstance(value, int):
                ints[i] += 1
            if isinstance(value, float):
                floats[i] += 1


    #print('nulls: {}\nstrs: {}\nints: {}\nfloats: {}\ndates: {}\njson_str_arrays: {}\n'.format(nulls, strs, ints, floats, dates, json_str_arrays))

    # Propose facets.
    suggestions = []
    for i, column in enumerate(columns):
        rv = []

        # Every column can be faceted by ColumnFacet
        rv.append({ 'label': 'this', 'params': { '_facet': column }})

        if json_str_arrays[i] > 0:
            rv.append({ 'label': 'this (array)', 'params': { '_facet_array': column }})

        if dates[i] > 0:
            rv.append({ 'label': 'this (date)', 'params': { '_facet_date': column }})
            rv.append({ 'label': 'this (year)', 'params': { '_facet_year': column }})
            rv.append({ 'label': 'this (month)', 'params': { '_facet_year_month': column }})

        suggestions.append(rv)

    return '''
__dux_facet_suggestions = {};
'''.format(json.dumps(suggestions))

def get_extra_body_script_for_dux_facets(template, database, table, columns, view_name, request, datasette):
    # Infer the facets to render. This is... complicated.
    # Look in the query string: _facet, _facet_date, _facet_array
    # Also look in metadata: https://docs.datasette.io/en/stable/facets.html#facets-in-metadata-json
    tables_metadata = datasette.metadata("tables", database=database) or {}
    table_metadata = tables_metadata.get(table) or {}
    configs = load_facet_configs(request, table_metadata)

    facet_params = []

    # column and simple feel duplicative?
    # { 'column': [ {'source': 'metadata', 'config': { 'simple': 'country_long' } } ] }
    for type, facets in configs.items():
        # Blech, _facet_size=max isn't actually a facet.
        if type == 'size':
            continue

        key = 'simple'
        if type != 'column':
            key = type

        for facet in facets:
            param = '_facet'
            if type != 'column':
                param += '_' + type

            # TODO: see issue #31
            # Huh, if I do _facet_array=tags, I still get simple as the inner key?
            # ... maybe this worked in vanilla Datasette because we compute all the facets,
            key = 'simple'
            facet_params.append({ 'param': param, 'column': facet['config'][key], 'source': facet['source'] })

    return '''
__dux_facets = {};
'''.format(json.dumps(facet_params))

