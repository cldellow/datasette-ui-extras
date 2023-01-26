import time
from datasette import facets
from datasette.utils import path_with_added_args

async def no_suggest(x):
    return []

async def no_facet_results(x):
    return [], []


def enable_yolo_facets():
    facets.DateFacet.suggest = no_suggest
    facets.ColumnFacet.suggest = no_suggest
    facets.ArrayFacet.suggest = no_suggest
    facets.DateFacet.facet_results = no_facet_results
    facets.ColumnFacet.facet_results = no_facet_results
    facets.ArrayFacet.facet_results = no_facet_results
    print('ok')
