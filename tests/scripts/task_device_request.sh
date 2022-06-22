#!/bin/bash
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# Usage: tests/scripts/task_device_request.sh [--device=device_type] [--port=port]
#

cd "$(dirname "$0")"
source "./util.sh" || exit 2

cd "$(get_repo_root)"

if [ "$1" == "--help" -o "$1" == "-h" ]; then
    echo "Usage: tests/scripts/task_device_request.sh [--device=device_type] [--port=port]"
    exit -1
fi

device_type="nrf5340dk_nrf5340_cpuapp"
if [ "$1" == "--port" ]; then
    device_type = "$1"
    shitf 1
fi

port=${DEFAULT_PORT}
if [ "$1" == "--port" ]; then
    port = "$1"
    shitf 1
fi

poetry run python -m microtvm_device.device_client \
    --port ${port} \
    --log-level=DEBUG \
    "request" \
    --device="${device_type}"
