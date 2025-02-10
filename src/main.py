# Copyright 2025 PoliTo
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Author: Tommaso Terzano <tommaso.terzano@polito.it> 
#                         <tommaso.terzano@gmail.com>
#  
# Info: This file is the main file of the VerifIt package.

import argparse
import os
import hjson
import run

def main():
    parser = argparse.ArgumentParser(description="VeriFit CLI tool")
    parser.add_argument("command", choices=["run"], help="Command to execute")

    args = parser.parse_args()

    if args.command == "run":
        run.verifit_run()

if __name__ == "__main__":
    main()
