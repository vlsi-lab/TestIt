import hjson
import os
import re
import importlib_resources as resources
import shutil

# Set this to True to enable debugging prints
DEBUG_MODE = True # TODO: REMOVE THIS LINE BEFORE RELEASE

# Redefine print() to be enabled only during debugging
def _PRINT(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

# Parses config.ver as an HJSON from the current working directory
def _load_config():
    config_path = os.path.join(os.getcwd(), "config.ver")
    
    if not os.path.exists(config_path):
        print("ERROR: config.ver not found in the current directory.")
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
    resource_path = resources.files("verifit") / filename
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