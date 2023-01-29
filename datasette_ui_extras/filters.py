from datasette import hookimpl
from datasette.filters import Filters, FilterArguments
def enable_yolo_arraycontains_filter():
    for fltr in Filters._filters:
        if fltr.key == 'arraycontains':
            fltr.sql_template = '"{c}" like \'%"\' || :{p} || \'"%\''
        if fltr.key == 'arraynotcontains':
            fltr.sql_template = '"{c}" not like \'%"\' || :{p} || \'"%\''

def patched_Filter_lookups(self):
    """Yields (lookup, display, no_argument) pairs"""
    yield 'exact', '=', False
    yield 'not', '!=', False
    for filter in self._filters:
        yield filter.key, filter.display, filter.no_argument

def enable_yolo_exact_filter():
    Filters._filters = [x for x in Filters._filters if x.key != 'exact' and x.key != 'not']
    Filters._filters_by_key = {f.key: f for f in Filters._filters}

    Filters.lookups = patched_Filter_lookups

    pass

async def yolo_filters_from_request(request, database, table, datasette):
    # Borrowed from https://github.com/simonw/datasette/blob/0b4a28691468b5c758df74fa1d72a823813c96bf/datasette/views/table.py#L347-L354
    filter_args = []
    for key in request.args:
        if not (key.startswith("_") and "__" not in key):
            for v in request.args.getlist(key):
                if not '__' in key:
                    key += '__exact'

                if key.endswith('__exact') or key.endswith('__not'):
                    filter_args.append((key, v))

    if not filter_args:
        return

    wheres = []
    params = {}
    descs = []

    param_index = 0
    for k, v in filter_args:
        op = 'exact'
        if k.endswith('__exact'):
            k = k[0:-7]
        elif k.endswith('__not'):
            op = 'not'
            k = k[0:-5]

        op_human = '=' if op == 'exact' else '!='
        wheres.append('"{c}" {op} :dux{param_index}'.format(
            c = k,
            op = op_human,
            param_index = param_index
        ))
        params['dux{}'.format(param_index)] = v

        human_desc_format = "{c} {op} {v}" if v.isdigit() else '{c} {op} "{v}"'

        human_desc = human_desc_format.format(c = k, op = op_human, v = v)

        # Is table.c an fkey to a pkey? If yes, fetch its label.
        expanded = await datasette.expand_foreign_keys(database, table, k, [v])
        if expanded:
            human_desc += ' ({})'.format(list(expanded.values())[0])
        descs.append(human_desc)
        param_index += 1
    return FilterArguments(
        wheres,
        params,
        descs
    )
