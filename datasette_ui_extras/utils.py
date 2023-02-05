from urllib.parse import urlparse, parse_qs

# Returns:
# - None if the edit UI ought not be shown
# - Information about which columns are editable
async def row_edit_params(datasette, request, database, table):
    # TODO: consider memoizing the response for a given database/table on the request object,
    # calling this 15,000 times might be slow.

    if not request:
        return None

    url = urlparse(request.url)
    qs = parse_qs(url.query)

    dux_edit_param = '_dux_edit' in qs and qs['_dux_edit'] == ['1']

    config = datasette.plugin_config('datasette-ui-extras', database=database)

    metadata_edit_param = config and 'editable' in config and table in config['editable']

    if not (dux_edit_param or metadata_edit_param):
        return None

    # Ensure user has permission to update this row
    visible, private = await datasette.check_visibility(
        request.actor,
        permissions=[
            ("update-row", (database, table)),
        ],
    )

    if not visible:
        return None

    # TODO: Determine the set of columns that are editable
    return {
        'title': {}
    }

