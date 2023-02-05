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
        RowView.dux_patched = True
        original_RowView_data = RowView.data
        async def patched_RowView_data(self, request, default_labels=False):
            data, template_data, templates = await original_RowView_data(self, request, default_labels)


            resolved = await self.ds.resolve_row(request)
            database = resolved.db.name
            table = resolved.table

            edit_mode = await row_edit_params(self.ds, request, database, table)

            if edit_mode:
                templates = tuple(['edit-row' + x[3:] for x in templates])
            return (data, template_data, templates)

        RowView.data = patched_RowView_data
