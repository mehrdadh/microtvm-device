# MicroTVM Device Python Package

A python package for managing microTVM devices on a server for the purpose of hardware CI testing, autotuning, etc.

## Dependencies
Main software dependency for this package is [VirtualBox](https://www.virtualbox.org/) since we use `vboxmanage` commands to manage device fleet, attach/detach them to/from the virtual boxes. In addition, the list of python dependencies are in [pyproject.toml](pyproject.toml) file. 

## Installation

### PyPi Package
```bash
pip3 install microtvm_device
```

### Install from source
Install [poetry package](https://python-poetry.org/docs/) to be able to build the pyproject. Then follow these steps to build the wheel package locally:
```bash
cd microtvm-device
poetry build
```
The wheel package is generates under `microtvm-device/dist`. You can use `pip3` to install it on your machine.

```bash
pip3 install microtvm-device/dist/microtvm_device...
```

## Setup Device Server
To run the device server run command bellow with a JSON file including information about various devices. [Here](./config/device_table.template.json) is a template of JSON file.
```
python3 -m microtvm_device.device_server --table-file=[DEVICE TABLE JSON FILE] <--port=[SERVER PORT]>

Note: If you are using the server in an envrionment with multiple users using VirtualBox, server should be run on an account with `sudo` access to all account to be able to inquery the USB attachments with any VirtualBox instance.
```

## Use Device Client

After running server you can run various command using device_client. Command includes `attach`, `detach`, `release`, `request` and `query`.

```bash
python3 -m microtvm_device.device_client <--port=[SERVER PORT]> COMMAND 
```
