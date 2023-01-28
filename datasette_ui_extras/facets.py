import time
from datasette import facets
from datasette.utils import path_with_added_args
from .facet_patches import ArrayFacet_facet_results

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

    targets = [facets.DateFacet, facets.ColumnFacet, facets.ArrayFacet]
    for target in targets:
        # Suppress facet suggestion
        target.suggest = no_suggest

        # Only compute facet results on JSON API calls
        target.facet_results = json_only(target.facet_results)

    # We'd like to smuggle info about the current page's rows to our extra_body_script
    # handler.
    patch_TableView_data()

