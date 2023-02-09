from sqlglot import parse_one, exp

def get_column_choices_from_check_constraints(sql):
    if not isinstance(sql, str):
        raise Exception('expected sql to be str but was {}'.format(sql))

    try:
        parsed = parse_one(sql)
    except:
        # They might have used something unparseable by sqlglot, fail gracefully.
        return {}

    # Returns a map from column name to permitted values, if
    # table defn has column defn of the form
    # x check (x in (...))
    rv = {}
    checks = list(parsed.find_all(exp.CheckColumnConstraint, exp.Check))

    for check in checks:
        if not isinstance(check.this, exp.In):
            continue

        in_ = check.this
        exprs = in_.expressions
        column = in_.this.this.this
        ok = []

        # Are all of the exprs literals?
        all_literal = True
        for expr in exprs:
            if not isinstance(expr, exp.Literal):
                all_literal = False
                break

            if expr.is_string:
                ok.append(expr.this)
            else:
                ok.append(int(expr.this))


        if not all_literal:
            continue

        if ok:
            rv[column] = ok

    return rv
