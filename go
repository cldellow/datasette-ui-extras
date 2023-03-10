#!/bin/bash
set -euo pipefail

datasette --host 0.0.0.0 --reload --setting trace_debug 1 --metadata metadata.json diy.db geonames.db cooking.db superuser.db --plugins-dir plugins --setting facet_time_limit_ms 2000 --setting sql_time_limit_ms 2000 --setting truncate_cells_html 500
