import argparse
from . import run

def main():
    parser = argparse.ArgumentParser(description="VeriFit CLI tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Define subparsers for individual commands
    run_parser = subparsers.add_parser("run", help="Run the verification process")
    setup_parser = subparsers.add_parser("setup", help="Setup the verification environment")
    
    # Add a flag to the 'run' command to indicate if the FPGA model has already been synthesized
    run_parser.add_argument(
        "--nobuild",
        action="store_true",
        help="Avoid building the model"
    )

    args = parser.parse_args()

    if args.command == "run":
        run.verifit_run(args.nobuild)
    elif args.command == "setup":
        run.verifit_setup()

if __name__ == "__main__":
    main()
