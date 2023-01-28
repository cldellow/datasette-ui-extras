from datasette import hookimpl
import markupsafe


@hookimpl
def render_cell(column, value):
    if column == 'image_url':
        return markupsafe.Markup(
        '<img src="{href}">'.format(
            href=markupsafe.escape(value),
        )
    )

    return None
