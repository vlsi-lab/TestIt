import hjson
import os
import re
import importlib_resources as resources
import shutil
import time
import subprocess
import threading
import rich

# Set this to True to enable debugging prints
DEBUG_MODE = False # TODO: REMOVE THIS LINE BEFORE RELEASE

# Redefine print() to be enabled only during debugging
def _PRINT(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

# Parses config.test as an HJSON from the current working directory
def _load_config():
    config_path = os.path.join(os.getcwd(), "config.test")
    
    if not os.path.exists(config_path):
        print("ERROR: config.test not found in the current directory.")
        return None

    with open(config_path, "r") as file:
        return hjson.load(file) 
    
# Checks if required targets exist in the target project Makefile
def _makefile_target_check():
    make_sanity_check = __makefile_has_target("deb-setup")
    make_sanity_check &= __makefile_has_target("sw-sim") & __makefile_has_target("sw-fpga")
    make_sanity_check &= __makefile_has_target("sim-build") &  __makefile_has_target("sim-run") 
    make_sanity_check &= __makefile_has_target("fpga-build") & __makefile_has_target("fpga-load")
    return make_sanity_check

# Copies a file from the package directory to the current working directory
def _copy_package_file(filename):
    resource_path = resources.files("testit") / filename
    shutil.copy(resource_path, os.getcwd())
    
# Checks if a specific target exists in the target project Makefile
def __makefile_has_target(target):
    targets = __extract_makefile_targets()
    return target in targets

# Extracts all top-level targets from a Makefile.
def __extract_makefile_targets():
    targets = []
    
    with open(f"{os.getcwd()}/Makefile", "r") as file:
        for line in file:
            match = re.match(r"^([a-zA-Z0-9_\-]+):", line)
            if match:
                targets.append(match.group(1))
                
    return targets

# Background thread to update time estimation frequently
def _update_time_estimation(progress, task_id):
    while not progress.tasks[task_id].finished:
        progress.refresh()
        time.sleep(0.2)  # Adjust this to control the update frequency
        
def _configuration_check(configuration, sweep_mode):
    if configuration['target']['type'] not in ["sim", "fpga"]:
        rich.print("   [bold red]ERROR: Invalid target type![/bold red]")
        rich.print(f"   {configuration['target']['type']} is neither 'sim' nor 'fpga'")
        return False

    if configuration['target']['type'] == "fpga" and (configuration['target']['usbPort'] == "" or configuration['target']['baudrate'] == ""): 
        rich.print("   [bold red]ERROR: invalid usbPort and/or baudrate![/bold red]")
        return False

    if sweep_mode:
        for test in configuration['tests']:
            if not any(isinstance(param["value"], list) for param in test["parameters"]):
                rich.print("   [bold red]ERROR: sweep mode requires every test to have at least one dynamic parameter![/bold red]")
                return False
            for param in test["parameters"]:
              if isinstance(param['value'], list):
                  if 'step' not in param or not isinstance(param['step'], int):
                      rich.print("   [bold red]ERROR: with sweep mode, each parameter requires a 'step' parameter to be defined as an integer![/bold red]")
                      return False
    
    return True

# Returns all the possible combinations of tests 
def _get_tot_sweep_iterations(data):
    sweep_parameters = []
    for test in data['tests']:
        tot = 1
        for parameter in test['parameters']:
            if isinstance(parameter['value'], list):
                tot *= int(abs(parameter['value'][0] - parameter['value'][1])/parameter['step']) + 1
        sweep_parameters.append(tot)
    
    return sweep_parameters