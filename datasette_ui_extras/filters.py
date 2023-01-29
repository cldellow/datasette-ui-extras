from datasette.filters import Filters
def enable_yolo_arraycontains():
    for fltr in Filters._filters:
        if fltr.key == 'arraycontains':
            fltr.sql_template = '"{c}" like \'%"\' || :{p} || \'"%\''
        if fltr.key == 'arraynotcontains':
            fltr.sql_template = '"{c}" not like \'%"\' || :{p} || \'"%\''
