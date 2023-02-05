from datasette import hookimpl

@hookimpl
def actor_from_request(request):
    return {'id': 'root'}

