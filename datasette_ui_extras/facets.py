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

def enable_yolo_facets():
    # TODO: do suggestions statically at the table level

    facets.Facet.get_configs = patched_get_configs

    targets = [facets.DateFacet, facets.ColumnFacet, facets.ArrayFacet]
    for target in targets:
        target.suggest = no_suggest
        target.facet_results = json_only(target.facet_results)
