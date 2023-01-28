from datasette import facets
from datasette.utils import (
    escape_sqlite,
    path_with_added_args,
    path_with_removed_args,
)
from datasette.database import QueryInterrupted


# monkey patch until https://github.com/simonw/datasette/pull/2008
# is merged
async def ArrayFacet_facet_results(self):
    # self.configs should be a plain list of columns
    facet_results = []
    facets_timed_out = []

    facet_size = self.get_facet_size()
    for source_and_config in self.get_configs():
        config = source_and_config["config"]
        source = source_and_config["source"]
        column = config.get("column") or config["simple"]
        # https://github.com/simonw/datasette/issues/448
        facet_sql = """
            with inner as ({sql}),
            deduped_array_items as (
                select
                    distinct j.value,
                    inner.{col}
                from
                    json_each([inner].{col}) j
                    join inner
            )
            select
                value as value,
                count(*) as count
            from
                deduped_array_items
            group by
                value
            order by
                count(*) desc, value limit {limit}
        """.format(
            col=escape_sqlite(column), sql=self.sql, limit=facet_size + 1
        )
        try:
            facet_rows_results = await self.ds.execute(
                self.database,
                facet_sql,
                self.params,
                truncate=False,
                custom_time_limit=self.ds.setting("facet_time_limit_ms"),
            )
            facet_results_values = []
            facet_results.append(
                {
                    "name": column,
                    "type": self.type,
                    "results": facet_results_values,
                    "hideable": source != "metadata",
                    "toggle_url": self.ds.urls.path(
                        path_with_removed_args(
                            self.request, {"_facet_array": column}
                        )
                    ),
                    "truncated": len(facet_rows_results) > facet_size,
                }
            )
            facet_rows = facet_rows_results.rows[:facet_size]
            pairs = self.get_querystring_pairs()
            for row in facet_rows:
                value = str(row["value"])
                selected = (f"{column}__arraycontains", value) in pairs
                if selected:
                    toggle_path = path_with_removed_args(
                        self.request, {f"{column}__arraycontains": value}
                    )
                else:
                    toggle_path = path_with_added_args(
                        self.request, {f"{column}__arraycontains": value}
                    )
                facet_results_values.append(
                    {
                        "value": value,
                        "label": value,
                        "count": row["count"],
                        "toggle_url": self.ds.absolute_url(
                            self.request, toggle_path
                        ),
                        "selected": selected,
                    }
                )
        except QueryInterrupted:
            facets_timed_out.append(column)

    return facet_results, facets_timed_out

facets.ArrayFacet.facet_results = ArrayFacet_facet_results
