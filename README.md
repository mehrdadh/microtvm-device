# MicroTVM Device Python Package

A python package for managing microTVM devices on a server for the purpose of hardware CI testing, autotuning, etc.

## Installation

```
pip3 install microtvm_device
```

## Setup Device Server
To run the device server run command bellow with a JSON file including information about various devices. [Here](./config/device_table.template.json) is a template of JSON file.
```
python -m microtvm_device.device_server --table-file=[DEVICE TABLE JSON FILE] <--port=[SERVER PORT]>
```

## Use Device Client

After running server you can run various command using device_client. Command includes `attach`, `detach`, `release`, `request` and `query`.

```
python -m microtvm_device.device_client <--port=[SERVER PORT]> COMMAND 
```
