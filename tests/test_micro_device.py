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

import sys
from time import sleep
import pytest
import argparse
import pathlib
import logging
import multiprocessing

from microtvm_device import device_server
from microtvm_device import device_client

SERVER_PORT = 4040


def init_server():
    input_args = argparse.Namespace()
    input_args.table_file = (
        pathlib.Path(__file__).parent / ".." / "config" / "device_table.template.jsonsdsd"
    ).resolve()
    input_args.port = SERVER_PORT

    device_server.ServerStart(input_args)


def run_server():
    proc = multiprocessing.Process(target=init_server, args=())
    proc.start()
    # wait till server is up.
    sleep(4)
    return proc


def test_server():
    server_proc = run_server()
    sleep(4)
    server_proc.terminate()


def test_query():
    server_proc = run_server()
    input_args = argparse.Namespace()
    input_args.port = SERVER_PORT
    input_args.func = device_client.query_device
    device_client.run_command(input_args)
    server_proc.terminate()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__] + sys.argv[1:]))
