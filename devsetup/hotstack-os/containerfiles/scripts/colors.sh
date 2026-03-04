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

# Color and status indicator constants for containerfile scripts
# Usage: source /usr/local/lib/colors.sh

# ============================================================================
# Color Constants
# ============================================================================
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m' # No Color

# ============================================================================
# Status Indicators
# ============================================================================
export OK="${GREEN}[OK]${NC}"
export ERROR="${RED}[ERROR]${NC}"
export WARNING="${YELLOW}[WARNING]${NC}"
export INFO="${BLUE}[INFO]${NC}"
export DONE="${GREEN}[DONE]${NC}"
export FAILED="${RED}[FAILED]${NC}"
