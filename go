#!/bin/bash
set -euo pipefail

datasette --reload --setting trace_debug 1 --metadata metadata.json global-power-plants.db cooking.db
