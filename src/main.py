# Copyright 2025 PoliTo
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Author: Tommaso Terzano <tommaso.terzano@polito.it> 
#                         <tommaso.terzano@gmail.com>
#  
# Info: This file is the main file of the VerifIt package.

import argparse
import run
import setup

def main():
    parser = argparse.ArgumentParser(description="VeriFit CLI tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add the "run" command
    run_parser = subparsers.add_parser("run", help="Run the verification process")

    # Add the "setup" command
    setup_parser = subparsers.add_parser("setup", help="Setup the verification environment")
    
    # Add a flag to indicate if the FPGA model has already been synthesized
    run_parser.add_argument(
        "--nosynth",
        action="store_true",  # Sets it to True if provided
        help="Specify if the FPGA model has already been synthesized"
    )

    args = parser.parse_args()

    if args.command == "run":
        run.verifit_run(fpga_synthesized=args.synthesized)  # Pass flag to the run function
    elif args.command == "setup":
        setup.verifit_setup()

if __name__ == "__main__":
    main()
