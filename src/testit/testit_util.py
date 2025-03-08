# Copyright (C) 2025 Politecnico di Torino
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import importlib.util
import json
import os
import subprocess
import sys
import threading

import numpy as np
import rich
import serial

# Set this to True to enable debugging prints
# TODO: REMOVE BEFORE RELEASE
DEBUG_MODE = False


def write_array(f, array, shape, indent=2):
    """Writes a numpy array to a file in a human-readable format.

    Args:
        f (file): The file object to write to.
        array (numpy.ndarray): The array to write.
        shape (tuple): The shape of the array.
        indent (int, optional): The number of spaces to indent the output. Defaults to 2.
    """
    flat_array = array.flatten()
    num_dims = len(shape)
    f.write(" " * indent)

    for i, value in enumerate(flat_array):

        f.write(f" {value}")

        if i < len(flat_array) - 1:
            f.write(",")
            # Insert a newline after every "row" (last dimension)
            if (i + 1) % shape[-1] == 0:
                f.write("\n" + " " * indent)

            # Insert a **blank line** when finishing a 2D block (2nd-to-last dimension)
            if num_dims > 2 and (i + 1) % (shape[-2] * shape[-1]) == 0:
                f.write("\n")

            # Insert **two blank outputLines** when finishing a 3D block
            if num_dims > 3 and (i + 1) % (shape[-3] * shape[-2] * shape[-1]) == 0:
                f.write("\n\n")

            # Insert **three blank outputLines** when finishing a 4D block, and so on...
            if num_dims > 4:
                for d in range(4, num_dims + 1):
                    if (i + 1) % np.prod(shape[-d:]) == 0:
                        f.write("\n" * (d - 2))

    f.write("\n" + " " * indent)


def _load_database(results_dir):
    """Loads the test results database from the specified directory.

    Args:
        results_dir (str): The directory containing the test results database.

    Returns:
        dict: The test results database. If the database does not exist, an empty dictionary is returned.
    """
    if os.path.exists(f"{results_dir}/test_results.json"):
        with open(f"{results_dir}/test_results.json", "r") as file:
            return json.load(file)
    return {}


def clear_database(result_dir):
    """Eliminates the existing database file.

    Args:
        result_dir (str): The directory containing the test results database.
    """
    if os.path.exists(f"{result_dir}/test_results.json"):
        os.remove(f"{result_dir}/test_results.json")


def append_results_to_report(result_dir, test_name, iteration, results):
    """Append results to the report database.

    Args:
        result_dir (str): The directory containing the test results database.
        test_name (str): The name of the test.
        iteration (int): The iteration number.
        results (list): The list of results to append.
    """
    db = _load_database(result_dir)

    print_deb(
        f"Appending results to report: {test_name}, iteration {iteration}, results: {results}"
    )

    # Ensure the test has a list initialized
    if test_name not in db:
        db[test_name] = []

    # Append new result
    for result in results:
        result_entry = {"iteration": iteration, **result}
        db[test_name].append(result_entry)

    print_deb(f"Database after appending: {db}")

    # Save back to JSON
    with open(f"{result_dir}/test_results.json", "w", encoding="utf-8") as file:
        json.dump(db, file, indent=4)


def dyn_load_func(function_name):
    """Dynamic loading of a function from 'testit_golden.py'.

    Args:
        function_name (str): The name of the function to load.

    Raises:
        ImportError: If the module is not found.
        AttributeError: If the function is
            not found in the module.

    Returns:
        function: The loaded function.
    """
    module_name = "testit_golden"
    module_path = os.path.join(os.getcwd(), f"{module_name}.py")

    if not os.path.exists(module_path):
        raise ImportError(
            f"Module {module_name} not found in current directory: {module_path}"
        )

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, function_name):
        raise AttributeError(f"Function {function_name} not found in {module_name}")

    return getattr(module, function_name)


def serial_rx_setup(ser: serial.Serial, serial_comm_queue, endword="&"):
    """Reads data from the serial port and puts it into a queue.
       Attention: comunications must end with the endword character.

    Args:
        ser (serial.Serial): The serial port object.
        serial_comm_queue (queue.Queue): The queue to put the received data.
        endword (str, optional): The character to end the communication. Defaults
            to "&".
    Raises:
        serial.SerialException: If the serial port is not open.
    """
    try:
        if not ser.is_open:
            raise serial.SerialException("Serial port not open")

        received = False
        while not received:
            # Read the data from the serial port
            line = ser.readline().decode("utf-8").rstrip()
            serial_comm_queue.put(line)
            print_deb(f">: {line}")
            if line:
                if endword in line:
                    received = True
                    print_deb(f"Received {endword}: end of serial transmission thread")
                    return
    except serial.SerialException as e:
        print(f"Serial exception: {e}")
    except Exception as e:
        print(f"An ERROR occurred: {e}")
    except KeyboardInterrupt:
        print("Keyboard interruption")
    finally:
        pass


def print_deb(*args, **kwargs):
    """Prints debug messages if DEBUG_MODE is enabled." """
    if DEBUG_MODE:
        print(*args, **kwargs)


def is_numpy_array(obj):
    """Check if the object is a numpy array.

    Args:
        obj (_type_): The object to check.

    Returns:
        bool: True if the object is a numpy array, False otherwise.
    """
    return isinstance(obj, np.ndarray)


def _run_command_threading(command):
    thread = threading.Thread(target=__run_command, args=(command,), daemon=True)
    thread.start()
    return thread


# If the command fails, the process will terminate and the script will exit
def __run_command(command):
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True
    )

    while True:
        output = process.stdout.readline()
        if output:
            if "ERROR" in output or "Error" in output or "error" in output:
                process.terminate()
                process.wait()
                rich.print(f"[bold red]CRITICAL ERROR: {output} failed![/bold red]")
                os._exit(1)

        error_output = process.stderr.readline()
        if error_output:
            if "ERROR" in output or "Error" in output or "error" in output:
                process.terminate()
                process.wait()
                rich.print(f"[bold red]CRITICAL ERROR: {output} failed![/bold red]")
                os._exit(1)

        # Check if process is still running
        if process.poll() is not None:
            break  # Exit loop when process completes

    process.wait()  # Ensure process is fully done before exiting


def get_sweep_parameters(iteration, parameters):
    """Get the sweep parameters for the current iteration.

    Args:
        iteration (int): The current iteration.
        parameters (list): The list of parameters to sweep.

    Returns:
        list: The sweep parameters for the current iteration.
    """
    sweep_parameters = []
    range_sizes = []
    param_ranges = []
    complete_parameters = []
    steps = []

    for parameter in parameters:
        if isinstance(parameter["value"], list):
            param_ranges.append(tuple(parameter["value"]))
            steps.append(parameter["step"])

    # Compute range sizes
    for (min_val, max_val), step in zip(param_ranges, steps):
        size = (max_val - min_val) // step + 1
        range_sizes.append(size)

    step_product = 1
    for idx, ((min_val, _), step) in enumerate(zip(param_ranges, steps)):
        if idx > 0:
            step_product *= range_sizes[idx - 1]
        param_value = min_val + ((iteration // step_product) % range_sizes[idx]) * step
        sweep_parameters.append(param_value)

    sweep_index = 0
    for param in parameters:
        if isinstance(param["value"], list):
            complete_parameters.append(sweep_parameters[sweep_index])
            sweep_index += 1
        else:
            complete_parameters.append(param["value"])

    return complete_parameters
