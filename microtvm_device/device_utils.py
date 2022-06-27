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

import argparse
import subprocess
import re
import os
import enum
import json
from tabulate import tabulate
import logging
import copy
import random
import grp
import getpass

VIRTUALBOX_VID_PID_RE = re.compile(r"0x([0-9A-Fa-f]{4}).*")

MICRO_DEVICE_TYPES = [
    "nucleo_f746zg",
    "stm32f746g_disco",
    "nrf5340dk_nrf5340_cpuapp",
    "nucleo_l4r5zi",
    "nano33ble",
    "due",
    "spresense"
]

VBOXMANAGE_CMD = subprocess.check_output(["which", "vboxmanage"], encoding="utf-8").replace("\n", "")

logging.basicConfig(level=logging.INFO)
LOG_ = logging.getLogger("Device Utils")

class MicroDevice(object):
    """A microTVM device instance."""

    def __init__(self, type: str, serial_number: str, vid_hex: str=None, pid_hex: str=None) -> None:
        """
        Parameters
        ----------
        _type : str
            Device type.
        _serial_number : str
            Device serial number.
        _vid_hex : str
            VID number.
        _pid_hex : str
            PID number.
        _is_taken : bool
            If device is aquired.
        _user : str
            Username who aquired this device.
        _enabled : bool
            True if device is enabled to use.
        """
        self._type = type
        self._serial_number = serial_number
        self._vid_hex = vid_hex
        self._pid_hex = pid_hex
        self._is_taken = False
        self._user = None
        self._enabled = True
        super().__init__()

    def GetSerialNumber(self) -> str:
        return self._serial_number

    def GetType(self) -> str:
        return self._type

    def GetVID(self) -> str:
        return self._vid_hex
    
    def GetPID(self) -> str:
        return self._pid_hex

    def SetType(self, type: str):
        self._type = type

    def SetSerialNumber(self, serial_number: str):
        self._serial_number = serial_number

    def SetVID(self, vid: str):
        self._vid_hex = vid
    
    def SetPID(self, pid: str):
        self._pid_hex = pid
    
    def SetTaken(self):
        self._is_taken = True

    def SetUser(self, user=None):
        if not user:
            self._user = "Unknown"
        else:
            self._user = user
        self.SetTaken()

    def Enable(self, status: str):
        self._enabled = status

    def Free(self):
        self._is_taken = False
        self._user = None


class GRPCSessionTasks(str, enum.Enum):
    SESSION_CLOSE = "session_close"
    SESSION_CLOSED = "session_closed"


class MicroTVMPlatforms:
    """An instance to keep all MicroDevice devices"""

    def __init__(self):
        """
        Parameters
        ----------
        _platforms : list[MicroDevice]
            List of MicroDevices.
        _serial_numbers : set[str]
            Set of serial numbers of all MicroDevices.
        _sessions : dict[str]
            A dictionary that keeps MicroDevices for each connected session.
        """
        self._platforms = list()
        self._serial_numbers = set()
        self._sessions = dict()

    def __str__(self):
        headers = ["#", "Type", "Serial", "Available", "User", "Enabled"]
        data = []
        for device in self._platforms:
            data.append(
                [
                    device.GetType(),
                    device.GetSerialNumber(),
                    not device._is_taken,
                    str(device._user),
                    device._enabled,
                ]
            )
        data = sorted(data, key=lambda l:l[0].lower(), reverse=False)
        message = "\n"
        message += str(tabulate(data, headers=headers, showindex='always'))
        return message

    def AddPlatform(self, device: MicroDevice):
        if device.GetSerialNumber() not in self._serial_numbers:
            self._serial_numbers.add(device.GetSerialNumber())
            self._platforms.append(device)

    def GetType(self, serial_number: str) -> str:
        """Returns device type if serial number exist in platforms, otherwise None."""
        for platform in self._platforms:
            if platform._serial_number == serial_number:
                return platform._type
        return None

    def GetPlatform(self, type: str, session_number: str, username: str) -> str:
        """Gets a MicroDevice from platform list."""
        candidate_platforms = []
        for platform in self._platforms:
            if platform._type == type and not platform._is_taken and platform._enabled:
                candidate_platforms.append(platform)

        if len(candidate_platforms) > 0:
            random_num = random.randint(0, len(candidate_platforms)-1)
            platform = candidate_platforms[random_num]
            platform._is_taken = True
            platform._user = username
            serial_number = platform.GetSerialNumber()
            self._sessions[session_number].append(serial_number)
            return copy.copy(platform)
        return None

    def ReleasePlatform(self, serial_number: str):
        for platform in self._platforms:
            if platform.GetSerialNumber() == serial_number:
                platform.Free()
                return
        LOG_.warning(f"SerialNumber {serial_number} was not found.")

    def EnablePlatform(self, serial_number: str, status: bool)-> bool:
        for platform in self._platforms:
            if platform.GetSerialNumber() == serial_number:
                platform.Enable(status)
                return True
        return False
    
    def GetAllDeviceTypes(self) -> list:
        micro_device_list = list()
        all_types = set()
        for platform in self._platforms:
            if platform.GetType() not in all_types:
                all_types.add(platform.GetType())
                micro_device_list.append(platform)
        return micro_device_list

    def GetDeviceWithType(self, device_type: str) -> MicroDevice:
        for platform in self._platforms:
            if platform.GetType() == device_type:
                return copy.copy(platform)
        return None

def _check_call(cmd, **kwargs) -> None:
    try:
        subprocess.run(cmd, capture_output=True, check=True, text=True, **kwargs)
    except Exception as err:
        error_msg = f"{err}\nstdout:\n{err.stdout}\nstderr:\n{err.stderr}"
        raise Exception(error_msg)

def LoadDeviceTable(table_file: str) -> MicroTVMPlatforms:
    """Load device table Json file to MicroTVMPlatforms."""
    with open(table_file, "r") as json_f:
        data = json.load(json_f)
        device_table = MicroTVMPlatforms()
        for device_type, config in data.items():
            for item in config["instances"]:
                new_device = MicroDevice(type=device_type, serial_number=item, 
                    vid_hex=config["vid_hex"], pid_hex=config["pid_hex"])
                device_table.AddPlatform(new_device)
    return device_table

def GetUsersFromGroup(group_name: str) -> list:
    """Return all users in a group on linux"""
    all_users = []
    groups = grp.getgrall()
    for group in groups:
        if group.gr_name == group_name:
            for user in group[3]:
                all_users.append(user)
    return all_users

def ParseVirtualBoxDevices(micro_device: MicroDevice, username: str=None) -> list:
    """Parse usb devices and return a list of devices maching microtvm_platform.
    This function returns one device per serial number and user.
    """
    if username:
        vboxusers = [username]
    else:
        vboxusers = GetUsersFromGroup("vboxusers")
    devices = []
    for user in vboxusers:
        output = subprocess.check_output(
            ["sudo", "-H", "-u", user, VBOXMANAGE_CMD, "list", "usbhost"], encoding="utf-8"
        )
        if "Host USB Devices:\n\n<none>\n\n" in output:
            logging.warning(f"User `{user}` cannot access USB information.")
            continue

        current_dev = {}
        for line in output.split("\n"):
            if not line.strip():
                if current_dev:
                    if "VendorId" in current_dev and "ProductId" in current_dev:
                        # Update VendorId and ProductId to hex
                        m = VIRTUALBOX_VID_PID_RE.match(current_dev["VendorId"])
                        if not m:
                            LOG_.warning("Malformed VendorId: %s", current_dev["VendorId"])
                            current_dev = {}
                            continue

                        m = VIRTUALBOX_VID_PID_RE.match(current_dev["ProductId"])
                        if not m:
                            LOG_.warning(
                                "Malformed ProductId: %s", current_dev["ProductId"]
                            )
                            current_dev = {}
                            continue

                        current_dev["vid_hex"] = (
                            current_dev["VendorId"]
                            .replace("(", "")
                            .replace(")", "")
                            .split(" ")[1]
                            .lower()
                        )
                        current_dev.pop("VendorId", None)

                        current_dev["pid_hex"] = (
                            current_dev["ProductId"]
                            .replace("(", "")
                            .replace(")", "")
                            .split(" ")[1]
                            .lower()
                        )
                        current_dev.pop("ProductId", None)

                        if (
                            current_dev["vid_hex"]
                            == micro_device.GetVID()
                            and current_dev["pid_hex"]
                            == micro_device.GetPID()
                        ):
                            devices.append(current_dev)
                    current_dev = {}
                # Line empty and a device is not created
                continue

            key, value = line.split(":", 1)
            value = value.lstrip(" ")
            current_dev[key] = value

        if current_dev:
            devices.append(current_dev)
    return devices


def ListConnectedDevices(micro_device: MicroDevice) -> list:
    """List all platforms connected to this hardware node. Returns a list of MicroDevice."""

    devices = ParseVirtualBoxDevices(micro_device)
    device_list = []
    for device in devices:
        new_device = MicroDevice(type=micro_device.GetType(), 
            serial_number=device["SerialNumber"], vid_hex=micro_device.GetVID(), pid_hex=micro_device.GetPID())
        if device["Current State"] == "Captured":
            new_device.SetUser()
        device_list.append(new_device)

    # Remove repetition in devices
    refined_list = []
    serial_list = []
    for device_1 in device_list:
        if device_1.GetSerialNumber() in serial_list:
            continue
        temp_devices = [device_1]
        serial_list.append(device_1.GetSerialNumber())

        for device_2 in device_list:
            if device_1.GetSerialNumber() == device_2.GetSerialNumber():
                temp_devices.append(device_2)

        device_added = False
        for device in temp_devices:
            if device._is_taken:
                refined_list.append(device)
                device_added = True
                continue
        if not device_added:
            refined_list.append(device)

    return refined_list


def DeviceIsAlive(device_type: str, serial: str) -> bool:
    devices = ListConnectedDevices(MicroDevice(device_type, serial_number=serial))
    for device in devices:
        if device.GetSerialNumber() == serial:
            return True
    return False

def VirtualBoxGetInfo(machine_uuid: str) -> dict:
    """
    Get virtual box information and return as a dictionary.
    """
    output = subprocess.check_output(
        ["vboxmanage", "showvminfo", machine_uuid], encoding="utf-8"
    )
    machine_info = {}
    for line in output.split("\n"):
        LOG_.debug(line)
        try:
            key, value = line.split(":", 1)
            value = value.lstrip(" ")
            # To capture multiple microTVM devices
            if key in machine_info:
                if machine_info[key] is list:
                    machine_info[key].append(value)
                else:
                    machine_info[key] = [machine_info[key], value]
            else:
                machine_info[key] = value
        except:
            continue
    LOG_.debug(f"machine info:\n{machine_info}")
    return machine_info


def virtualbox_is_live(machine_uuid: str):
    """
    Return True if this virtualbox is running
    """
    machine_info = VirtualBoxGetInfo(machine_uuid)
    if "running" in machine_info["State"]:
        return True
    return False


def attach_command(args):
    attach(MicroDevice(type=args.microtvm_platform, serial_number=args.serial), args.vm_path)


def attach(micro_device: MicroDevice, vm_path: str):
    """
    Attach a microTVM platform to a virtualbox.
    """
    usb_devices = ParseVirtualBoxDevices(micro_device, username=getpass.getuser())
    found = False
    for dev in usb_devices:
        if dev["SerialNumber"] == micro_device.GetSerialNumber():
            vid_hex = dev["vid_hex"]
            pid_hex = dev["pid_hex"]
            serial = dev["SerialNumber"]
            dev_uuid = dev["UUID"]
            found = True
            break

    if not found:
        LOG_.warning(f"Device list:\n{usb_devices}")
        raise ValueError(f"Device S/N {micro_device.GetSerialNumber()} not found.")

    with open(
        os.path.join(vm_path, ".vagrant", "machines", "default", "virtualbox", "id")
    ) as f:
        machine_uuid = f.read()

    if serial and dev_uuid:
        rule_args = [
            "VBoxManage",
            "usbfilter",
            "add",
            "0",
            "--action",
            "hold",
            "--name",
            "test device",
            "--target",
            machine_uuid,
            "--vendorid",
            vid_hex,
            "--productid",
            pid_hex,
            "--serialnumber",
            serial,
        ]

        # Check if already attached
        machine_info = VirtualBoxGetInfo(machine_uuid)
        if "SerialNumber" in machine_info:
            if serial in machine_info["SerialNumber"]:
                LOG_.info(f"Device {serial} already attached.")
                return

        # if virtualbox_is_live(machine_uuid):
        #     raise RuntimeError("VM is running.")

        _check_call(
            ["VBoxManage", "controlvm", machine_uuid, "usbattach", dev_uuid]
        )
        LOG_.info(f"USB with S/N {serial} attached.")
        return
    else:
        raise Exception(
            f"Device with vid={vid_hex}, pid={pid_hex}, serial={serial!r} not found:\n{usb_devices!r}"
        )


def detach(micro_device: MicroDevice, vm_path: str):
    with open(
        os.path.join(vm_path, ".vagrant", "machines", "default", "virtualbox", "id")
    ) as f:
        machine_uuid = f.read()

    usb_devices = ParseVirtualBoxDevices(micro_device, username=getpass.getuser())
    found = False
    for dev in usb_devices:
        if dev["SerialNumber"] == micro_device.GetSerialNumber():
            dev_uuid = dev["UUID"]
            found = True
            break

    if not found:
        LOG_.warning(f"Serial {micro_device.GetSerialNumber()} not found in usb devies.")
        LOG_.warning(usb_devices)
        return
    _check_call(
        ["VBoxManage", "controlvm", machine_uuid, "usbdetach", dev_uuid]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="Action to perform.")

    parser_attach = subparsers.add_parser(
        "attach", help="Attach a microTVM device to a virtual machine."
    )
    parser_attach.set_defaults(func=attach_command)

    parser_attach.add_argument("--serial", help="microTVM targer serial number.")
    parser_attach.add_argument("--vm-path", help="Location of virtual machine.")

    parser.add_argument(
        "--microtvm-platform",
        required=True,
        choices=MICRO_DEVICE_TYPES,
        help=("microTVM target platform for list."),
    )

    parser.add_argument("--log-level", default=None, help="Log level.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.log_level:
        LOG_.basicConfig(level=args.log_level)
    else:
        LOG_.basicConfig(level="INFO")

    args.func(args)
