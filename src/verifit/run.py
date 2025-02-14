from . import run_util 
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from rich.status import Status
import rich
from . import verifit
import os

def verifit_run(=False):
    
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

    progress = Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),        
        transient=True,
    ) 
    
    print("Setting up VerifIt project...")

    # Check the presence of the required Makefile targets
    if not run_util._makefile_target_check() :
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

    # If the target is an FPGA board, load the bitstream, then setup the serial connection and GDB
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

    # Run the verification campaign
    task = progress.add_task("Running tests...", total=data['target']['iterations'] * len(data['tests']))

    for test_iteration in range(data['target']['iterations']):
        if not verEnv.gen_datasets():
          rich.print(f"  [bold red]ERROR: Dataset generation failed![/bold red]")

        for test in data['tests']:
            if not verEnv.launch_test(app_name=test['name'], iteration=test_iteration, pattern=rf"{data['target']['outputFormat']}", output_tags=data['target']['outputTags'], timeout_t=100):
                rich.print(f"  [bold red]ERROR: Test {test['name']} failed because of GDB timeout[/bold red]")
                exit(1)
            else:
                progress.update(task, advance=1, description=f"[cyan]{test_iteration}/{data['target']['iterations']}: {test['name']}")

    rich.print("[bold green]All tests run![/bold green]")
    rich.print("VerifIt campaign completed")

# If necessary, generates the necessary files for the VerifIt package: verifit_golden.py and config.ver
def verifit_setup():
    current_directory = os.getcwd()
    if os.path.exists(f"{current_directory}/verifit_golden.py"):
        rich.print("[orange]WARNING: 'verifit_golden.py' already exists in the current directory.[\orange]")    
    else: 
        run_util._copy_package_file("templates/verifit_golden.py")
        rich.print("Generation of 'verifit_golden.py' [bold green]successful[/bold green]!")
    
    if os.path.exists(f"{current_directory}/config.ver"):
        rich.print("[orange]WARNING: 'config.ver' already exists in the current directory.[\orange]")
    else:
        run_util._copy_package_file("templates/config.ver")
        rich.print("Generation of 'config.ver' [bold green]successful[/bold green]!")
