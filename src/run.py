# Copyright 2025 PoliTo
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#<
# Author: Tommaso Terzano <tommaso.terzano@polito.it> 
#                         <tommaso.terzano@gmail.com>
#  
# Info: This file includes the definition of the "run" command of VerifIt, which effectivly runs the 
# verification campaign using verifit.py

import hjson
import verifit
import os
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from rich.status import Status
import rich
import time
import subprocess
import re

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

def _make_target_exists(cmd):
    """Check if a Makefile target exists."""
    return subprocess.run(["which make ", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def _extract_makefile_targets(makefile_path="Makefile"):
    """Extracts all top-level targets from a Makefile."""
    targets = []
    
    with open(makefile_path, "r") as file:
        for line in file:
            match = re.match(r"^([a-zA-Z0-9_\-]+):", line)  # Match 'target_name:'
            if match:
                targets.append(match.group(1))

    return targets

def _makefile_has_target(target, makefile_path="Makefile"):
    """Checks if a specific target exists in a Makefile."""
    targets = _extract_makefile_targets(makefile_path)
    return target in targets

#__________________________________________________________________________________________________#
# External functions

def verifit_run():
    # Load the configuration file
    data = _load_config()
    if data is None:
        rich.print("[bold red]ERROR: config.ver not found![/bold red")
        rich.print("Please run the 'setup' command first.")
        exit(1)
    #TODO: Check for the verfit_golden.py file
    
    current_directory = os.getcwd()

    # Debug the configuration hjson
    _PRINT(data)

    # Create the VerifIt object
    verEnv = verifit.VerifIt(data)

    progress = Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),        
        transient=True,
    ) 
    
    print("Setting up VerifIt project...")

    # Sanity check on the target project makefile
    with Status(" [cyan]Checking target project...[/cyan]", spinner="dots") as status:
        make_sanity_check = _makefile_has_target("sw", current_directory) 
        make_sanity_check &= _makefile_has_target("sim-build", current_directory) &  _makefile_has_target("sim-run", current_directory) 
        make_sanity_check &= _makefile_has_target("fpga-build", current_directory) & _makefile_has_target("fpga-load", current_directory)
    
    if not make_sanity_check:
        rich.print("  [bold red]ERROR: Makefile sanity check failed![/bold red]")
        exit(1)
    else:
        rich.print("  Makefile sanity check [bold green]successful[/bold green]!")

    # Build the model
    with Status(" [cyan]Building model...[/cyan]", spinner="dots") as status:
        build_success = verEnv.build_model()

    if not build_success:
        rich.print("  [bold red]ERROR: Model build failed![/bold red]")
        exit(1)
    else:
        rich.print("  Model build [bold green]successful[/bold green]!")

    # If the target is an FPGA board, load the model, then setup the serial connection and GDB
    if data['target']['type'] == "fpga":
        with Status(f" [cyan]Loading model on FPGA board {data['target']['name']}...[/cyan]", spinner="dots") as status:
            load_success = verEnv.load_fpga_model()   

        if not load_success:
            rich.print(f"  [bold red]ERROR: Model load on FPGA board {data['target']['name']} failed![/bold red]")
            exit(1)
        else:
            rich.print(f"  Model load on FPGA board {data['target']['name']} [bold green]successful[/bold green]!")     

        with Status(" [cyan]Setting up serial connection...[/cyan]", spinner="dots") as status:
            serial_setup_success = verEnv.serial_begin()
        
        if not serial_setup_success:
            rich.print("  [bold red]ERROR: Serial setup failed![/bold red]")
            exit(1)
        else:
            rich.print("  Serial setup [bold green]successful[/bold green]!")

        with Status(" [cyan]Setting up GDB...[/cyan]", spinner="dots") as status:
            gdb_setup_success = verEnv.setup_gdb()

        if not gdb_setup_success:
            rich.print("  [bold red]ERROR: GDB setup failed![/bold red]")
            exit(1)
        else:
            rich.print("  GDB setup [bold green]successful[/bold green]!")

    task = progress.add_task("Running tests...", total=data['target']['iterations'] * len(data['target']['tests']))

    # Run the verification campaign
    for iteration in range(data['target']['iterations']):
        verEnv.gen_datasets()
        for test in data['target']['tests']:
            if not verEnv.launch_test(app_name=test['name'], iteration=iteration, pattern=rf"{data['target']['outputFormat']}", output_tags=test['outputTags'], timeout=100):
                rich.print(f"  [bold red]ERROR: Test {test['name']} failed because of GDB timeout[/bold red]")
                exit(1)
            else:
                progress.update(task, advance=1, description=f"[cyan]{iteration}/{data['target']['iterations']}: {test['name']}")

    rich.print("[bold green]All tests run![/bold green]")
    rich.print("VerifIt campaign completed")
    
    

    
