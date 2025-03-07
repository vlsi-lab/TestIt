import argparse
from . import run

def main():
    parser = argparse.ArgumentParser(description="TestIt CLI tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Define subparsers for individual commands
    run_parser = subparsers.add_parser("run", help="Run the verification process")
    subparsers.add_parser("setup", help="Set up the verification environment")
    report_parser = subparsers.add_parser("report", help="Generate a report based on the test results")
    
    # Add a flag to the 'run' command to indicate if the FPGA model has already been synthesized
    run_parser.add_argument(
        "--nobuild",
        action="store_true",
        help="Avoid building the model"
    )
    
    run_parser.add_argument(
        "--sweep",
        action="store_true",
        help="Test every possible combination of parameters"
    )

    run_parser.add_argument(
        "--mammamia",
        action="store_true",
        help="Let's cook some pasta"
    )

    # Sorting key argument
    report_parser.add_argument(
        "--sort_key",
        type=str,
        help="Specify the key to sort by (e.g., 'Cycles', 'Outcome')"
    )

    # Sorting order flag (default: ascending, use flag for descending)
    report_parser.add_argument(
        "--descending",
        action="store_true",
        help="Sort results in descending order (default: ascending)"
    )

    args = parser.parse_args()

    if args.command == "run":
        run.testit_run(args.nobuild, args.mammamia, args.sweep)
    elif args.command == "setup":
        run.testit_setup()
    elif args.command == "report":
        run.testit_report(args.sort_key, not args.descending)

if __name__ == "__main__":
    main()
