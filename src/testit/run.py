from . import run_util 
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn, SpinnerColumn
from rich.status import Status
import rich
from . import testit
import os
import threading
import queue
import time

import os
import time
import json
from rich import print
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, SpinnerColumn
from rich.status import Status

def testit_run(no_build=False, italian_mode=False, sweep_mode=False):
    
    current_directory = os.getcwd()

    # Load the configuration file
    data = run_util._load_config()
    if data is None:
        rich.print("[bold red]ERROR: config.test not found![/bold red]")
        rich.print("Please run the 'setup' command first.")
        exit(1)
    
    if not os.path.exists(f"{current_directory}/testit_golden.py"):
        rich.print("[bold red]ERROR: testit_golden.py not found![/bold red]")
        rich.print("Please run the 'setup' command first.")
        exit(1)    

    # Create the TestIt object
    testEnv = testit.TestItEnv(data)
    testEnv.clear_results()
    
    if not italian_mode:
      rich.print("[cyan]Setting up TestIt project...[/cyan]")
    else:
      rich.print("\n[bold green][][/bold green][white][][/white][bold red][][/bold red]\n")
      rich.print("[cyan]Bringing salted water to boil...[/cyan]")

    # Check the presence of the required Makefile targets
    if not run_util._makefile_target_check():
        rich.print(" - [bold red]ERROR: Target project Makefile check failed![/bold red]")
        rich.print("   Please ensure that the Makefile contains the required targets")
        exit(1)
    elif not run_util._configuration_check(data, sweep_mode):
        rich.print(" - [bold red]ERROR: there is an issue with config.test critical parameters![/bold red]")
        exit(1)
    else:
        if not italian_mode:
            rich.print(" - Target project Makefile and config.test check [bold green][OK][/bold green]")
        else:
            rich.print(" - Nonna's recipe [bold green][READ][/bold green]")

    if not no_build:
        # Build the model
        if not italian_mode:
            with Status(" - [cyan]Building model...[/cyan]", spinner="dots") as status:
                build_success = testEnv.build_model()
        else:
            with Status(" - [cyan]Making pasta dough...[/cyan]", spinner="dots") as status:
                build_success = testEnv.build_model()

        if not build_success:
            rich.print(" - [bold red]ERROR: Model build failed![/bold red]")
            exit(1)
        else:
            if not italian_mode:
                rich.print(" - Model build [bold green][OK][/bold green]")
            else:
                rich.print(" - Hand-made pasta [bold green][DONE][/bold green]")

    # If the target is an FPGA board, load the model, then setup the serial connection and GDB
    if data['target']['type'] == "fpga":
        if not italian_mode:
            with Status(f" - [cyan]Loading model on FPGA board {data['target']['name']}...[/cyan]", spinner="dots") as status:
                load_success = testEnv.load_fpga_model()
        else:
            with Status(f" - [cyan]Frying the soffritto in a pan...[/cyan]", spinner="dots") as status:
                load_success = testEnv.load_fpga_model() 

        if not load_success:
            rich.print(f" - [bold red]ERROR: Model load on FPGA board {data['target']['name']} failed![/bold red]")
            rich.print("   Please ensure that the FPGA board is connected and powered on")
            exit(1)
        else:
            if not italian_mode:
                rich.print(f" - Model load on FPGA board {data['target']['name']} [bold green][OK][/bold green]")
            else:
                rich.print(f" - Soffritto [bold green][COOKED][/bold green]")     

        if not italian_mode:
            with Status(" - [cyan]Setting up serial connection...[/cyan]", spinner="dots") as status:
                serial_setup_success = testEnv.serial_begin()
        else:
            with Status(" - [cyan]Opening a couple of pelati cans...[/cyan]", spinner="dots") as status:
                serial_setup_success = testEnv.serial_begin()
        
        if not serial_setup_success:
            rich.print(" - [bold red]ERROR: Serial setup failed![/bold red]")
            rich.print("   Please ensure that the serial port is correctly configured")
            exit(1)
        else:
            if not italian_mode:
                rich.print(" - Serial setup [bold green][OK][/bold green]")
            else:
                rich.print(" - Pelati cans [bold green][OPENED][/bold green]")
        
        deb_setup_success = testEnv.setup_deb()
        if not deb_setup_success:
            rich.print(f" - [bold red]ERROR: Debugger setup failed![/bold red]")
            exit(1)
        else:
            if not italian_mode:
                rich.print(" - Debugger setup [bold green][OK][/bold green]")
            else:
                rich.print(" - Basil leaves [bold green][PICKED][/bold green]") 

        if not italian_mode:
            with Status(" - [cyan]Setting up GDB...[/cyan]", spinner="dots") as status:
                gdb_setup_success = testEnv.setup_gdb()
        else:
            with Status(" - [cyan]Cooking the pomodoro sauce...[/cyan]", spinner="dots") as status:
                gdb_setup_success = testEnv.setup_gdb()

        if not gdb_setup_success:
            rich.print(" - [bold red]ERROR: GDB setup failed![/bold red]")
            exit(1)
        else:
            if not italian_mode:
                rich.print(" - GDB setup [bold green][OK][/bold green]")
            else:
                rich.print(" - Pomodoro sauce [bold green][COOKED][/bold green]") 
    else:
        if not italian_mode:
            rich.print(" - Model build phase [bold green][SKIPPED][/bold green]")
        else:
            rich.print(" - Using [bold green][STORE-BOUGHT][/bold green] tomato sauce")

    if not italian_mode:
        rich.print("[cyan]\nRunning verification campaign...[/cyan]")
    else:
        rich.print("[cyan]\nThrowing in the pasta...[/cyan]")

    with Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),   
        SpinnerColumn(),   
        transient=True,
    ) as progress:
        
        # Compute the total test iterations
        if not sweep_mode:
            test_iterations = data['target']['iterations']
        else:
            sweep_test_iterations = run_util._get_tot_sweep_iterations(data)

            test_index = 0
            for test in data['tests']:
                test['totIterations'] = sweep_test_iterations[test_index]
                test['currentIteration'] = 0
                test_index += 1

            if isinstance(sweep_test_iterations, list):
                test_iterations = max(sweep_test_iterations)
            else:
                test_iterations = sweep_test_iterations

            rich.print("[yellow]WARNING[/yellow]: sweep mode is active, TestIt will cycle through each possible combination of parameters for each test")
            
        if not italian_mode:
            task_message = " - Running tests..."
        else:
            task_message = " - Cooking..."

        task = progress.add_task(task_message, total=test_iterations, start=False)
        start = False
        
        test_counter = 0

        test_duration_report = {}

        for test_iteration in range(test_iterations):
            if not testEnv.gen_datasets(sweep_mode, test_iteration):
                rich.print(f" - [bold red]ERROR: Dataset generation failed![/bold red]")
                exit(1)

            update_list_of_tests = False

            # Prepare a list for the current iteration's test durations
            test_duration_report[test_iteration] = []

            for test in data['tests']:
                start_time = time.time()

                # Re-setup debugger every 10 tests if using FPGA
                if test_counter == 10 and data['target']['type'] == "fpga":
                    test_counter = 0
                    testEnv.stop_gdb()
                    testEnv.stop_deb()

                    deb_setup_success = testEnv.setup_deb()
                    if not deb_setup_success:
                        deb_setup_again_success = testEnv.setup_deb()
                        if not deb_setup_again_success:
                            rich.print(f" - [bold red]ERROR: Failed to re-setup debugger[/bold red]")
                            exit(1)

                    gdb_setup_success = testEnv.setup_gdb()
                    if not gdb_setup_success:
                        gdb_setup_again_success = testEnv.setup_gdb()
                        if not gdb_setup_again_success:
                            rich.print(f" - [bold red]ERROR: Failed to re-setup GDB[/bold red]")
                            exit(1)
                else:
                    test_counter += 1
                    

                if not testEnv.launch_test(app_name=test['appName'], iteration=test_iteration, pattern=rf"{test['outputFormat']}", output_tags=test['outputTags'], timeout_t=1000):
                    rich.print(f" - [bold red]ERROR: Test {test['appName']} failed because of GDB timeout[/bold red]")
                    exit(1)

                if not start:
                    progress.start_task(task)
                    start = True
                
                progress.update(task, advance=1, 
                                description=f" - [cyan]{test_iteration + 1}/{test_iterations}: {test['appName']}", 
                                refresh=True)
            
                if sweep_mode:
                    test['currentIteration'] += 1
                    if test['currentIteration'] == test['totIterations']:
                        test_to_be_removed_name = test['appName']
                        new_data = [p for p in data['tests'] if p['appName'] != test_to_be_removed_name]
                        update_list_of_tests = True

                end_time = time.time()
                duration = end_time - start_time

                test_duration_report[test_iteration].append({
                    "name": test['appName'],
                    "duration": duration
                })

            if update_list_of_tests:
                data['tests'] = new_data

        if data['target']['type'] == "fpga":
            testEnv.stop_deb()

        # Output the time duration of the tests
        report_dir = data['report']['dir']
        os.makedirs(report_dir, exist_ok=True)
        json_path = os.path.join(report_dir, "test_durations.json")
        with open(json_path, "w") as f:
            json.dump(test_duration_report, f, indent=2)

        if not italian_mode:
            rich.print(" - All tests [bold green][RAN][/bold green]")
            rich.print("\nTestIt campaign [bold green]completed![/bold green]")
        else:
            rich.print(" - Pasta [bold green][COOKED][/bold green]!")
            rich.print("\n[bold green]A tavola![/bold green]")


# If necessary, generates the necessary files for the TestIt package: testit_golden.py and config.test
def testit_setup():
    current_directory = os.getcwd()
    if os.path.exists(f"{current_directory}/testit_golden.py"):
        rich.print("[yellow]WARNING: 'testit_golden.py' already exists in the current directory.[/yellow]")    
    else: 
        run_util._copy_package_file("templates/testit_golden.py")
        rich.print("Generation of 'testit_golden.py' [bold green][OK][/bold green]")
    
    if os.path.exists(f"{current_directory}/config.test"):
        rich.print("[yellow]WARNING: 'config.test' already exists in the current directory.[/yellow]")
    else:
        run_util._copy_package_file("templates/config.test")
        rich.print("Generation of 'config.test' [bold green][OK][/bold green]")

# Generates a report of the last verification campaign
def testit_report(sort_key, ascending):
    # Load the configuration file
    data = run_util._load_config()

    # Create the TestIt object
    testEnv = testit.TestItEnv(data)

    testEnv.gen_report(sort_key, ascending)