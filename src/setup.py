# Copyright 2025 PoliTo
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Author: Tommaso Terzano <tommaso.terzano@polito.it> 
#                         <tommaso.terzano@gmail.com>
#  
# Info: This file includes the definition of the "setup" command of VerifIt. It generates a configuration .ver file if 
# it does not exist along with verifit_golden.py, which is used to define golden function(s). Both files are generated
# simply by copying the files in the templates/ directory of VerifIt, which contains fully commented examples of both
# config.ver and verifit_golden.py.

import os
import rich
import pkg_resources
import shutil

def _copy_package_file(filename):
    resource_path = pkg_resources.resource_filename("your_package", filename)
    shutil.copy(resource_path, os.getcwd())

def verifit_setup():
    current_directory = os.getcwd()
    if os.path.exists(f"{current_directory}/verifit_golden.py"):
        rich.print("[orange]WARNING: 'verifit_golden.py' already exists in the current directory.[\orange]")
        return
    else: 
        _copy_package_file("templates/verifit_golden.py")
        rich.print("Generation of 'verifit_golden.py' [bold green]successful[/bold green]!")
    
    if os.path.exists(f"{current_directory}/config.ver"):
        rich.print("[orange]WARNING: 'config.ver' already exists in the current directory.[\orange]")
        return
    else:
        _copy_package_file("templates/config.ver")
        rich.print("Generation of 'config.ver' [bold green]successful[/bold green]!")


