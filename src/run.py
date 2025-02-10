# Copyright 2025 PoliTo
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Author: Tommaso Terzano <tommaso.terzano@polito.it> 
#                         <tommaso.terzano@gmail.com>
#  
# Info: This file includes the definition of the "run" command of VerifIt, which effectivly runs the 
# verification campaign using verifit.py

import hjson
import verifit
import os

# Set this to True to enable debugging prints
DEBUG_MODE = True

#__________________________________________________________________________________________________#
# Internal functions

# Redefine print() to be enabled only during debugging
def _PRINT(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

def _load_config():
    """Loads config.ver from the current working directory."""
    config_path = os.path.join(os.getcwd(), "config.ver")
    
    if not os.path.exists(config_path):
        print("ERROR: config.ver not found in the current directory.")
        return None

    with open(config_path, "r") as file:
        return hjson.load(file)    

#__________________________________________________________________________________________________#
# External functions

def verifit_run():
    # Load the configuration file
    data = _load_config()

    # Debug the configuration hjson
    _PRINT(data)

    # Create the VerifIt object
    env = verifit.VerifIt(data)

    # Build the model 
    env.build_model()

    # If the target is an FPGA board, setup the serial connection and GDB
    if data['target']['type'] == "fpga":
        env.serial_begin()
        env.setup_deb()
    
    # Run the verification campaign
    for iteration in range(data['target']['iterations']):
        env.gen_datasets()
        for test in data['target']['tests']:
            env.launch_test(app_name=test['name'], iteration=iteration, additional_info=f"Iteration {iteration} on {data['target']['iterations']}", 
                            pattern=rf"{data['target']['outputFormat']}", output_tags=test['outputTags'], timeout=100)
    
    

    
