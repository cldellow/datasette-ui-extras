from pluggy import HookimplMarker
from pluggy import HookspecMarker

hookspec = HookspecMarker("datasette_ui_extras")
hookimpl = HookimplMarker("datasette_ui_extras")

# Conceptually, this is a firstresult=True hook. However, we support async
# awaitables, so we need to get all the results and await them.
@hookspec()
def edit_control(datasette, database, table, column, row, value, metadata):
    """Return the name of the edit control class to use, and optionally some configuration."""
