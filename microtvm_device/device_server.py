# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from concurrent import futures
import logging
import argparse
import grpc
import random

from . import microDevice_pb2
from . import microDevice_pb2_grpc
from . import device_utils
from .device_utils import MicroDevice, MicroTVMPlatforms
from .device_utils import GRPCSessionTasks

PLATFORMS = None
SESSION_NUM_MAX_LEN = 10
LOG_ = None

LOG_ = logging.getLogger("MicroTVM Device Server")

def LoadAttachedDevices(args: argparse.Namespace) -> MicroTVMPlatforms:
    """
    Load MicroTVM USB devices to a MicroTVMPlatforms.

    return: attached_devices
    """
    table = device_utils.LoadDeviceTable(args.table_file)
    
    # Return a fake list of devices for testing
    if args.dry_run:
        return table

    all_device_types = table.GetAllDeviceTypes()
    attached_devices = MicroTVMPlatforms()

    for micro_device in all_device_types:
        device_list = device_utils.ListConnectedDevices(micro_device)
        for new_device in device_list:
            # Update type based on Device Table since some device share the same (vid, pid).
            new_device_type = table.GetType(new_device.GetSerialNumber())
            
            if new_device_type is None:
                continue
            
            new_device.SetType(new_device_type)
            attached_devices.AddPlatform(new_device)
    return attached_devices


def Initialize(args):
    platforms = LoadAttachedDevices(args)
    return platforms


class RPCRequest(microDevice_pb2_grpc.RPCRequestServicer):
    global PLATFORMS

    def RPCDeviceRequest(self, request, context):
        assert request.type
        assert request.session_number
        assert request.user
        micro_device = PLATFORMS.GetPlatform(
            request.type, request.session_number, request.user
        )
        if micro_device:
            LOG_.debug(f"Platform {micro_device.GetSerialNumber()} assigned.")
            LOG_.debug(PLATFORMS)
            return microDevice_pb2.DeviceReply(serial_number=micro_device.GetSerialNumber(), 
                vid=micro_device.GetVID(), pid=micro_device.GetPID())
        else:
            return microDevice_pb2.DeviceReply(serial_number="")            

    def RPCDeviceRelease(self, request, context):
        assert request.type
        assert request.serial_number
        PLATFORMS.ReleasePlatform(serial_number=request.serial_number)
        LOG_.debug(PLATFORMS)
        return microDevice_pb2.DeviceReply()

    def RPCDeviceIsAlive(self, request, context):
        assert request.type

        return microDevice_pb2.DeviceReply(
            serial_number=request.serial_number,
            is_alive=device_utils.DeviceIsAlive(
                platform=request.type, serial=request.serial_number
            ),
        )

    def RPCSessionRequest(self, request, context):
        sess_num = "".join(
            ["{}".format(random.randint(0, 9)) for num in range(0, SESSION_NUM_MAX_LEN)]
        )
        # Add a new session
        PLATFORMS._sessions[sess_num] = []
        return microDevice_pb2.SessionMessage(session_number=sess_num)

    def RPCSessionClose(self, request, context):
        metadict = dict(context.invocation_metadata())
        print(metadict)

        assert request.session_number

        logging.debug(f"Closing session {{{request.session_number}}}.")
        for serial_num in PLATFORMS._sessions[request.session_number]:
            PLATFORMS.ReleasePlatform(serial_num)
            logging.debug(f"Platform {serial_num} released.")
        return microDevice_pb2.SessionMessage(
            session_number=request.session_number,
            task=GRPCSessionTasks.SESSION_CLOSED.value,
        )
    
    def RPCDeviceRequestList(self, request, context):
        return microDevice_pb2.StringMessage(
            text=str(PLATFORMS)
        )

    def RPCDeviceRequestEnable(self, request, context):
        status = PLATFORMS.EnablePlatform(serial_number=request.serial_number, status=True)
        LOG_.debug(PLATFORMS)
        if status:
            return microDevice_pb2.StringMessage(text="Enable Success.")
        else:
            return microDevice_pb2.StringMessage(text="Enable failed.")
    
    def RPCDeviceRequestDisable(self, request, context):
        status = PLATFORMS.EnablePlatform(serial_number=request.serial_number, status=False)
        LOG_.debug(PLATFORMS)
        if status:
            return microDevice_pb2.StringMessage(text="Disable Success.")
        else:
            return microDevice_pb2.StringMessage(text="Disable failed.")
    
    def RPCGetDeviceTypeInfo(self, request, context):
        assert request.type
        micro_device = PLATFORMS.GetDeviceWithType(device_type=request.type)
        return microDevice_pb2.DeviceReply(vid=micro_device.GetVID(), pid=micro_device.GetPID())

def ServerStart(args):
    global PLATFORMS
    PLATFORMS = Initialize(args)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    microDevice_pb2_grpc.add_RPCRequestServicer_to_server(RPCRequest(), server)
    server.add_insecure_port(f"[::]:{args.port}")
    server.start()
    LOG_.info("Server started...!")
    LOG_.info(PLATFORMS)
    server.wait_for_termination()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--table-file",
        type=str,
        required=True,
        help="Json file include serial number of all instances.",
    )
    parser.add_argument("--port", type=int, default=50051, help="RPC port number.")
    parser.add_argument("--log-level", default=None, help="Log level.")
    parser.add_argument("--dry-run", default=False, action="store_true")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.log_level:
        logging.basicConfig(level=args.log_level)

    ServerStart(args)
