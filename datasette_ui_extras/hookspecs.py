from pluggy import HookimplMarker
from pluggy import HookspecMarker

hookspec = HookspecMarker("datasette_ui_extras")
hookimpl = HookimplMarker("datasette_ui_extras")

@hookspec(firstresult=True)
def edit_control(datasette, database, table, column):
    """Return the name of the edit control class to use."""
