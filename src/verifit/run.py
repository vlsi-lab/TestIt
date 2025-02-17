from . import run_util 
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn, SpinnerColumn
from rich.status import Status
import rich
from . import verifit
import os

def verifit_run(no_build=False, italian_mode=False):
    
    current_directory = os.getcwd()

    # Load the configuration file
    data = run_util._load_config()
    if data is None:
        rich.print("[bold red]ERROR: config.ver not found![/bold red")
        rich.print("Please run the 'setup' command first.")
        exit(1)
    
    if not os.path.exists(f"{current_directory}/verifit_golden.py"):
        rich.print("[bold red]ERROR: verifit_golden.py not found![/bold red")
        rich.print("Please run the 'setup' command first.")
        exit(1)    

    # Create the VerifIt object
    verEnv = verifit.VerifItEnv(data)
    
    if not italian_mode:
      rich.print("[cyan]Setting up VerifIt project...[/cyan]")
    else:
      rich.print("\n[bold green][][/bold green][white][][/white][bold red][][/bold red]\n")
      rich.print("[cyan]Bringing salted water to boil...[/cyan]")

    # Check the presence of the required Makefile targets
    if not run_util._makefile_target_check() :
        rich.print(" - [bold red]ERROR: Target project Makefile check failed![/bold red]")
        rich.print(" - Please ensure that the Makefile contains the required targets")
        exit(1)
    else:
        if not italian_mode:
            rich.print(" - Target project Makefile sanity check [bold green][OK][/bold green]")
        else:
            rich.print(" - Nonna's recipe [bold green][READ][/bold green]")

    if not no_build:
        # Build the model
        if not italian_mode:
            with Status(" [cyan]Building model...[/cyan]", spinner="dots") as status:
                build_success = verEnv.build_model()
        else:
            with Status(" [cyan]Cutting onions...[/cyan]", spinner="dots") as status:
                build_success = verEnv.build_model()

        if not build_success:
            rich.print(" - [bold red]ERROR: Model build failed![/bold red]")
            exit(1)
        else:
            if not italian_mode:
                rich.print(" - Model build [bold green][OK][/bold green]")
            else:
                rich.print(" - Onions [bold green][CUT][/bold green]")

    # If the target is an FPGA board, load the bitstream, then setup the serial connection and GDB
    if data['target']['type'] == "fpga":
        if not italian_mode:
            with Status(f" [cyan]Loading model on FPGA board {data['target']['name']}...[/cyan]", spinner="dots") as status:
                load_success = verEnv.load_fpga_model()   
        else:
            with Status(f" [cyan]Frying the onions in a pan...[/cyan]", spinner="dots") as status:
                load_success = verEnv.load_fpga_model() 

        if not load_success:
            rich.print(f" - [bold red]ERROR: Model load on FPGA board {data['target']['name']} failed![/bold red]")
            rich.print("   Please ensure that the FPGA board is connected and powered on")
            exit(1)
        else:
            if not italian_mode:
                rich.print(f" - Model load on FPGA board {data['target']['name']} [bold green][OK][/bold green]")
            else:
                rich.print(f" - Soffritto {data['target']['name']} [bold green][DONE][/bold green]")     

        if not italian_mode:
            with Status(" [cyan]Setting up serial connection...[/cyan]", spinner="dots") as status:
                serial_setup_success = verEnv.serial_begin()
        else:
            with Status(" [cyan]Opening a couple of pelati cans...[/cyan]", spinner="dots") as status:
                serial_setup_success = verEnv.serial_begin()
        
        if not serial_setup_success:
            rich.print(" - [bold red]ERROR: Serial setup failed![/bold red]")
            rich.print("   Please ensure that the serial port is correctly configured")
            exit(1)
        else:
            if not italian_mode:
                rich.print(" - Serial setup [bold green][OK][/bold green]")
            else:
                rich.print(" - Pelati [bold green][OPENED][/bold green]")

        if not italian_mode:
            with Status(" [cyan]Setting up GDB...[/cyan]", spinner="dots") as status:
                gdb_setup_success = verEnv.setup_deb()
        else:
            with Status(" [cyan]Cooking the pomodoro sauce...[/cyan]", spinner="dots") as status:
                gdb_setup_success = verEnv.setup_deb()

        if not gdb_setup_success:
            rich.print(" - [bold red]ERROR: GDB setup failed![/bold red]")
            exit(1)
        else:
            if not italian_mode:
                rich.print(" - GDB setup [bold green][OK][/bold green]")
            else:
                rich.print(" - Pomodoro sauce [bold green][DONE][/bold green]") 

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
        # Run the verification campaign
        if not italian_mode:
          task_message = " - Running tests..."
        else:
          task_message = " - Cooking..."

        task = progress.add_task(task_message, total=data['target']['iterations'] * len(data['tests']), start=False)
        start = False

        for test_iteration in range(data['target']['iterations']):
            if not verEnv.gen_datasets():
              rich.print(f" - [bold red]ERROR: Dataset generation failed![/bold red]")
              exit(1)

            for test in data['tests']:
                if not verEnv.launch_test(app_name=test['appName'], iteration=test_iteration, pattern=rf"{test['outputFormat']}", output_tags=test['outputTags'], timeout_t=1000):
                    rich.print(f" - [bold red]ERROR: Test {test['appName']} failed because of GDB timeout[/bold red]")
                    exit(1)
                if not start:
                    progress.start_task(task)
                    start = True

                progress.update(task, advance=1, description=f" - [cyan]{test_iteration + 1}/{data['target']['iterations']}: {test['appName']}", refresh=True)
        
        if not italian_mode:
            rich.print(" - All tests [bold green][RAN][/bold green]")
            rich.print("\nVerifIt campaign completed!")
        else:
            rich.print(" - Pasta [bold green][COOKED][/bold green]")
            rich.print("\nA tavola!")

# If necessary, generates the necessary files for the VerifIt package: verifit_golden.py and config.ver
def verifit_setup():
    current_directory = os.getcwd()
    if os.path.exists(f"{current_directory}/verifit_golden.py"):
        rich.print("[yellow]WARNING: 'verifit_golden.py' already exists in the current directory.[/yellow]")    
    else: 
        run_util._copy_package_file("templates/verifit_golden.py")
        rich.print("Generation of 'verifit_golden.py' [bold green][OK][/bold green]")
    
    if os.path.exists(f"{current_directory}/config.ver"):
        rich.print("[yellow]WARNING: 'config.ver' already exists in the current directory.[/yellow]")
    else:
        run_util._copy_package_file("templates/config.ver")
        rich.print("Generation of 'config.ver' [bold green][OK][/bold green]")

# Generates a report of the last verification campaign
def verifit_report():
    # Load the configuration file
    data = run_util._load_config()

    # Create the VerifIt object
    verEnv = verifit.VerifItEnv(data)

    verEnv.gen_report()