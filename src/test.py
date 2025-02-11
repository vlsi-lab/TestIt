from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from rich.status import Status
import rich
import time

def run_tests_with_progress(test_apps, iterations):
    """Runs tests with a real-time progress bar in the terminal."""
    with Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),        
        transient=True,
    ) as progress:
        task = progress.add_task("Running tests...", total=len(test_apps) * iterations)

        for i in range(1, iterations + 1):
            for test in test_apps:
                time.sleep(1)  # Simulate test execution
                progress.update(task, advance=1, description=f"[cyan]Running {test} (Iteration {i})")

    # Now print the final message
    rich.print("[bold green]All tests completed successfully![/bold green]")


rich.print("[cyan]Setting up VerifIt...[/cyan]")

# Build the model
with Status(" [cyan]Building model...[/cyan]", spinner="dots") as status:
    time.sleep(3)  # Simulate model build
    build_success = True

if not build_success:
    rich.print("  [bold red]Model build failed![/bold red]")
    exit(1)
else:
    rich.print("  [bold green]Model build successful![/bold green]")


# Example Usage
test_apps = ["test1", "test2", "test3"]
run_tests_with_progress(test_apps, iterations=5)
