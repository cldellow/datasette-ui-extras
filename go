#!/bin/bash
set -euo pipefail

datasette --reload --metadata metadata.json global-power-plants.db
