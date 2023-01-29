from datasette.database import QueryInterrupted
from datasette.facets import Facet
from datasette.utils import (
    escape_sqlite,
    path_with_added_args,
    path_with_removed_args,
)

class YearFacet(Facet):
    type = "year"

    async def suggest(self):
        return []

    async def facet_results(self):
        facet_results = []
        facets_timed_out = []
        args = dict(self.get_querystring_pairs())
        facet_size = self.get_facet_size()
        for source_and_config in self.get_configs():
            config = source_and_config["config"]
            source = source_and_config["source"]
            column = config.get("column") or config["simple"]
            # TODO: does this query break if inner sql produces value or count columns?
            facet_sql = """
                select substr(date({col}), 1, 4) as value, count(*) as count from (
                    {sql}
                )
                where date({col}) is not null
                group by substr(date({col}), 1, 4) order by count desc, value limit {limit}
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
                        "toggle_url": path_with_removed_args(
                            self.request, {"_facet_year": column}
                        ),
                        "truncated": len(facet_rows_results) > facet_size,
                    }
                )
                facet_rows = facet_rows_results.rows[:facet_size]
                for row in facet_rows:
                    selected = str(args.get(f"{column}__like")) == str(row["value"]) + '%'
                    if selected:
                        toggle_path = path_with_removed_args(
                            self.request, {f"{column}__like": str(row["value"]) + '%'}
                        )
                    else:
                        toggle_path = path_with_added_args(
                            self.request, {f"{column}__like": row["value"] + '%'}
                        )
                    facet_results_values.append(
                        {
                            "value": row["value"],
                            "label": row["value"],
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

class YearMonthFacet(Facet):
    type = "year_month"

    async def suggest(self):
        return []

    async def facet_results(self):
        facet_results = []
        facets_timed_out = []
        args = dict(self.get_querystring_pairs())
        facet_size = self.get_facet_size()
        for source_and_config in self.get_configs():
            config = source_and_config["config"]
            source = source_and_config["source"]
            column = config.get("column") or config["simple"]
            # TODO: does this query break if inner sql produces value or count columns?
            facet_sql = """
                select substr(date({col}), 1, 7) as value, count(*) as count from (
                    {sql}
                )
                where date({col}) is not null
                group by substr(date({col}), 1, 7) order by count desc, value limit {limit}
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
                        "toggle_url": path_with_removed_args(
                            self.request, {"_facet_year_month": column}
                        ),
                        "truncated": len(facet_rows_results) > facet_size,
                    }
                )
                facet_rows = facet_rows_results.rows[:facet_size]
                for row in facet_rows:
                    selected = str(args.get(f"{column}__like")) == str(row["value"]) + '%'
                    if selected:
                        toggle_path = path_with_removed_args(
                            self.request, {f"{column}__like": str(row["value"]) + '%'}
                        )
                    else:
                        toggle_path = path_with_added_args(
                            self.request, {f"{column}__like": row["value"] + '%'}
                        )
                    facet_results_values.append(
                        {
                            "value": row["value"],
                            "label": row["value"],
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

class StatsFacet(Facet):
    type = "stats"

    async def suggest(self):
        return []

    async def facet_results(self):
        facet_results = []
        facets_timed_out = []
        args = dict(self.get_querystring_pairs())
        facet_size = self.get_facet_size()
        for source_and_config in self.get_configs():
            config = source_and_config["config"]
            source = source_and_config["source"]
            column = config.get("column") or config["simple"]
            # TODO: does this query break if inner sql produces value or count columns?
            facet_sql = """
with
xs as ({sql}),
with_ids as (select row_number() over () as id, {col} as value from xs),
ntiles as (select id, value, ntile(100) over (order by value) percentile from with_ids)
select percentile, min(value), max(value) from ntiles
group by 1
having percentile in (1, 50, 90, 95, 99, 100)
order by 1
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
                        "toggle_url": path_with_removed_args(
                            self.request, {"_facet_stats": column}
                        ),
                        "truncated": len(facet_rows_results) > facet_size,
                    }
                )
                facet_rows = facet_rows_results.rows[:facet_size]

                percentile_groups = {}
                for row in facet_rows:
                    percentile_groups['{}_min'.format(row[0])] = row[1]
                    percentile_groups['{}_max'.format(row[0])] = row[2]

                facet_rows = [
                    ('max', percentile_groups['100_max']),
                    ('p99', percentile_groups['99_max']),
                    ('p95', percentile_groups['95_max']),
                    ('p90', percentile_groups['90_max']),
                    ('median', percentile_groups['50_min']),
                    ('min', percentile_groups['1_min']),
                ]

                for value, count in facet_rows:
                    facet_results_values.append(
                        {
                            "value": value,
                            "label": value,
                            "count": count,
                            "toggle_url": '#',
                            "selected": False,
                        }
                    )
            except QueryInterrupted:
                facets_timed_out.append(column)

        return facet_results, facets_timed_out
