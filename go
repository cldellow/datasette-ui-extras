#!/bin/bash
set -euo pipefail

datasette --reload --setting trace_debug 1 --metadata metadata.json cooking.db superuser.db --plugins-dir plugins --setting facet_time_limit_ms 2000 --setting sql_time_limit_ms 2000
