from datasette import hookimpl

@hookimpl
def permission_allowed(actor, action, resource):
    #print('actor={} action={} resource={}'.format(actor, action, resource))
    return True
