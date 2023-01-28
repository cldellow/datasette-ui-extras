#!/bin/bash
set -euo pipefail

datasette --reload --setting trace_debug 1 --metadata metadata.json cooking.db superuser.db --plugins-dir plugins
