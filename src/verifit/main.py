import argparse
from . import run

def main():
    parser = argparse.ArgumentParser(description="VeriFit CLI tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Define subparsers for individual commands
    run_parser = subparsers.add_parser("run", help="Run the verification process")
    
    # Add a flag to the 'run' command to indicate if the FPGA model has already been synthesized
    run_parser.add_argument(
        "--nobuild",
        action="store_true",
        help="Avoid building the model"
    )

    run_parser.add_argument(
        "--mammamia",
        action="store_true",
        help="Let's cook some pasta"
    )

    args = parser.parse_args()

    if args.command == "run":
        run.verifit_run(args.nobuild, args.mammamia)
    elif args.command == "setup":
        run.verifit_setup()
    elif args.command == "report":
        run.verifit_report()

if __name__ == "__main__":
    main()
