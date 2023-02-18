from datasette.utils.asgi import Forbidden
from .utils import row_edit_params

def enable_yolo_edit_row_pages():
    # We also enable a new template: edit-row.
    from datasette.views.row import RowView

    # We can't capture the original RowView.data function outside of this fn
    # due to a circular import issue, so do it here.
    #
    # In tests, this can lead to patching it twice, so remember if we've patched it.
    if not hasattr(RowView, 'dux_patched'):
        patch_RowView_data(RowView)
        patch_Datasette_resolve_row()


def patch_RowView_data(RowView):
    RowView.dux_patched = True
    original_RowView_data = RowView.data
    async def patched_RowView_data(self, request, default_labels=False):
        data, template_data, templates = await original_RowView_data(self, request, default_labels)


        resolved = await self.ds.resolve_row(request)
        database = resolved.db.name
        table = resolved.table


        edit_mode = await row_edit_params(self.ds, request, database, table)

        if resolved.pks == 'dux-insert':
            templates = tuple(['insert-row' + x[3:] for x in templates])
        elif edit_mode:
            templates = tuple(['edit-row' + x[3:] for x in templates])
        return (data, template_data, templates)


    RowView.data = patched_RowView_data

def patch_Datasette_resolve_row():
    from datasette.app import Datasette, ResolvedRow

    original_Datasette_resolve_row = Datasette.resolve_row
    async def patched_Datasette_resolve_row(self, request):
        pks = request.url_vars['pks']

        if pks != 'dux-insert':
            return await original_Datasette_resolve_row(self, request)

        db, table_name, _ = await self.resolve_table(request)

        # Determine the columns that we should show the user.
        # Proposal: show all columns except single-column primary keys.
        all_columns = list(await db.execute('SELECT "name", "type", "notnull", "dflt_value", "pk" FROM pragma_table_info(?)', [table_name]))

        single_column_pk = True if len([col for col in all_columns if col['pk']]) == 1 else False

        columns = [col for col in all_columns if not single_column_pk or not col['pk']]

        sql = 'SELECT ' + ', '.join([
            'NULL AS "{}"'.format(col['name'])
            for col in columns
        ])

        # db, table, sql, params, pks, pk_values, row
        params = {}
        pk_values = []
        row = []
        return ResolvedRow(db, table_name, sql, params, pks, pk_values, row)

    Datasette.resolve_row = patched_Datasette_resolve_row
