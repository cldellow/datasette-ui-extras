from datasette import hookimpl

@hookimpl
def permission_allowed(action):
    return True
