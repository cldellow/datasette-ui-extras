import time
from datasette import facets
from datasette.utils import path_with_added_args

DateFacet_suggest = facets.DateFacet.suggest
ColumnFacet_suggest = facets.ColumnFacet.suggest
ArrayFacet_suggest = facets.ArrayFacet.suggest

DateFacet_facet_results = facets.DateFacet.facet_results
ColumnFacet_facet_results = facets.ColumnFacet.facet_results
ArrayFacet_facet_results = facets.ArrayFacet.facet_results

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

def enable_yolo_facets():
    facets.DateFacet.suggest = no_suggest
    facets.ColumnFacet.suggest = no_suggest
    facets.ArrayFacet.suggest = no_suggest

    facets.DateFacet.facet_results = json_only(DateFacet_facet_results)
    facets.ColumnFacet.facet_results = json_only(ColumnFacet_facet_results)
    facets.ArrayFacet.facet_results = json_only(ArrayFacet_facet_results)
