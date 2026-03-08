#!/bin/bash
# Copyright Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Prepare runtime configuration files for HotsTac(k)os

set -e

# Source common utilities
# shellcheck source=scripts/common.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/common.sh"

echo "Preparing HotsTac(k)os runtime configuration..."

# Load environment configuration
load_env_file

# Prepare runtime configurations
prepare_all_configs

echo ""
echo "Configuration complete!"
echo ""
echo -e "${INFO} Runtime configs prepared in: $CONFIGS_RUNTIME_DIR"
echo -e "${INFO} Runtime scripts prepared in: $SCRIPTS_RUNTIME_DIR"
echo -e "${INFO} clouds.yaml copied to: ${HOTSTACK_DATA_DIR}/clouds.yaml and $(pwd)/clouds.yaml"
echo ""
