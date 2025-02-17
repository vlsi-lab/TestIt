import importlib.util
import json
import os
import serial
import numpy as np
import sys

# Set this to True to enable debugging prints
# TODO: REMOVE BEFORE RELEASE
DEBUG_MODE = False

def _write_array(f, array, shape, indent=2):    
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

# Loads the existing database or initializes a new one
def _load_database(dir):
    if os.path.exists(f"{dir}/test_results.json"):
        with open(f"{dir}/test_results.json", "r") as file:
            return json.load(file)
    return {}

# Eliminates the existing database file
def _clear_database(dir):
    if os.path.exists(f"{dir}/test_results.json"):
        with open(f"{dir}/test_results.json", "w") as file:
            file.write("")

# Appends results to the report database
def _append_results_to_report(dir, test_name, iteration, results):
    
    db = _load_database(dir)

    PRINT_DEB(f"Appending results to report: {test_name}, iteration {iteration}, results: {results}")

    # Ensure the test has a list initialized
    if test_name not in db:
        db[test_name] = []

    # Append new result
    result_entry = {"iteration": iteration, **results}
    db[test_name].append(result_entry)

    PRINT_DEB(f"Database after appending: {db}")

    # Save back to JSON
    with open(f"{dir}/test_results.json", "w") as file:
        json.dump(db, file, indent=4)

# Dynamically load a function from 'verifit_golden.py'
def _dyn_load_func(function_name):
    spec = importlib.util.spec_from_file_location("verifit_golden", os.getcwd())
    module = importlib.util.module_from_spec(spec)
    sys.modules["verifit_golden"] = module
    spec.loader.exec_module(module)
    return getattr(module, function_name)
    
# SUPER-IMPORTANT: Every communication by the SW application MUST end with an endword character, which is by default "&".
def _serial_rx_setup(ser, serial_comm_queue, endword="&"):
    try:
        if not ser.is_open:
            raise serial.SerialException("Serial port not open")
        
        received = False
        while not received:
            # Read the data from the serial port
            line = ser.readline().decode('utf-8').rstrip()
            serial_comm_queue.put(line)
            PRINT_DEB(f">: {line}")
            if line:
                if endword in line:
                    received = True
                    PRINT_DEB(f"Received {endword}: end of serial transmission thread")
                    return
                elif "ERROR" in line:
                    print("FAILED VERIFICATION!")
                    exit(1)
    except serial.SerialException as e:
        print(f"Serial exception: {e}")
    except Exception as e:
        print(f"An ERROR occurred: {e}")
    except KeyboardInterrupt:
        print("Keyboard interruption")
    finally:
        pass
    
def PRINT_DEB(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)