# Copyright 2025 PoliTo
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Author: Tommaso Terzano <tommaso.terzano@polito.it> 
#                         <tommaso.terzano@gmail.com>
#   functions to run a verification campaign.

import subprocess
import re
import time
import serial
import pexpect
import threading
import queue
import random
import os
import importlib
import json
import numpy as np

# Info: Python library of VerifIt. It   all the necessary
# Set this to True to enable debugging prints
DEBUG_MODE = False

# Define the name of the internal result database
DB_FILE = "test_results.json"

def PRINT_DEB(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

class VerifIt:
    def __init__(self, config):
        self.cfg = config
        self.results = []
        self.it_times = []

    def reset_all(self):
        self.results = []
        self.it_times = []
        if self.ser.is_open:
          self.ser.close()
        self.ser = None
        self.serial_queue = None
        self.serial_thread = None
        self.gdb = None
        self.project_root = None

    def clear_results(self):
        self.results = []

    # Synthesis & Simulation methods
    
    # Build the model for either the simulation tool or the FPGA board
    # If the model has already been synthesized, i.e. fpga_synthesized=True, the method will skip the synthesis step
    def build_model(self, fpga_synthesized=True):
        if self.cfg['target']['type'] == "fpga":
          if fpga_synthesized:
            cmd = f"make fpga-build board={self.cfg['target']['name']}"
            subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if ("ERROR" in cmd.stderr) or ("ERROR" in cmd.stderr):
                print(cmd.stderr)
                return False
            else:
                return True
        else:
          cmd = f"make sim-build tool={self.cfg['target']['name']}"
          subprocess.run(cmd, shell=True, capture_output=True, text=True)
          if ("ERROR" in cmd.stderr) or ("ERROR" in cmd.stderr):
              print(cmd.stderr)
              return False
          else:
              return True
    
    def load_fpga_model(self):
        cmd = f"make fpga-load board={self.cfg['target']['name']}"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if ("ERROR" in cmd.stderr) or ("ERROR" in cmd.stderr):
            print(cmd.stderr)
            return False
        else:
            return True
  
    # FPGA interface methods
    
    # Set-up serial communication
    def serial_begin(self):
        try:
            self.ser = serial.Serial(self.cfg['target']['usbPort'], self.cfg['target']['baudrate'], timeout=1)
            # Serial communication with the FPGA board is managed using queues
            self.serial_queue = queue.Queue()
            
            if self.ser.is_open:
                print("Connection successful")
                return True
            else:
                print("Failed to open the connection")
                return False
        except serial.SerialException as e:
            print(f"Serial exception: {e}")
            return False
        except Exception as e:
            print(f"An ERROR occurred: {e}")
            return False

    # Set-up GDB
    def setup_deb(self):
        gdb_cmd = f"""
        cd {self.project_root}
        $RISCV/bin/riscv32-unknown-elf-gdb ./sw/build/main.elf
        """
        self.gdb = pexpect.spawn(f"/bin/bash -c '{gdb_cmd}'")
        self.gdb.expect('(gdb)')
        self.gdb.sendline('set remotetimeout 2000')
        self.gdb.expect('(gdb)')
        self.gdb.sendline('target remote localhost:3333')
        self.gdb.expect('(gdb)')

        if self.gdb.isalive():
            PRINT_DEB("GDB process is still running.")
        else:
            PRINT_DEB("GDB process has terminated.")
            if self.gdb.exitstatus is not None:
                print(f"GDB exit status: {self.gdb.exitstatus}")
            if self.gdb.signalstatus is not None:
                print(f"GDB terminated by signal: {self.gdb.signalstatus}")
            exit(1)
            
    # Stop GDB
    def stop_deb(self):
        self.gdb.sendcontrol('c')
        self.gdb.terminate()

    # Launch a test by compiling the target application and loading it into the FPGA flash via GDB
    # The name of the application has to be one of the names set in config.hjson
    # It's possible to print additional information for debugging purpouses.
    # The pattern indicated the expected output pattern to receive via GDB.
    # If the application times out, the verification campaign is interrupted.
    def launch_test(self, app_name, iteration, pattern=r'(\d+):(\d+):(\d+)', output_tags=None, timeout_t=0):
        # Set default output ids
        if output_tags is None:
            output_tags = ["ID", "Cycles", "Outcome"]

        # Test using the FPGA board
        if self.cfg['target']['type'] == "fpga":

            # Check that the serial connection is still open, otherwise stop the verification campaign
            if not self.ser.is_open:
                print("ERROR: Serial port is not open!")
                exit(1) 

            # Set up the serial communication thread and attach it the serial queue
            self.serial_thread = threading.Thread(target=_serial_rx_setup, args=(self.ser, self.serial_queue))

            # Start the serial thread
            self.serial_thread.start()

            # Compile the application
            app_compile_cmd = f"make sw app={app_name}"
            
            result_compilation = subprocess.run(app_compile_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_compilation.stderr) or ("Error" in result_compilation.stderr):
                print(result_compilation.stderr)
                return
            else:
                PRINT_DEB("Compilation successful!")
            
            # Run the testbench with gdb
            self.gdb.sendline('load')
            self.gdb.expect('(gdb)')

            try:
              output = self.gdb.read_nonblocking(size=100, timeout=1)
              PRINT_DEB("Current gdb output:", output)
            except pexpect.TIMEOUT:
              PRINT_DEB("No new output from GDB.")
              self.gdb.terminate()
              return False

            # Set a breakpoint at the exit and wait for it
            self.gdb.sendline('b _exit')
            self.gdb.expect('(gdb)')
            self.gdb.sendline('continue')
            try:
              self.gdb.expect('Breakpoint', timeout=timeout_t)
            except pexpect.TIMEOUT:
              PRINT_DEB("Timeout reached.")
              self.gdb.terminate()
              return False
            
            # Wait for serial to finish
            self.serial_thread.join()

            # Recover the lines
            lines = []
            while not self.serial_queue.empty():
                lines.append(self.serial_queue.get())
        
        # Test using the simulation tool
        else:
            # Compile the application
            app_compile_cmd = f"make sw app={app_name}"
            result_compilation = subprocess.run(app_compile_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_compilation.stderr) or ("Error" in result_compilation.stderr):
                print(result_compilation.stderr)
                return
            else:
                PRINT_DEB("Compilation successful!")

            # Launch the simulation test
            sim_cmd = f"make sim-run app={app_name}"
            result_sim = subprocess.run(sim_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_sim.stderr) or ("Error" in result_sim.stderr):
                print(result_sim.stderr)
                return
            else:
                PRINT_DEB("Simulation successful!")

            # Read the output file
            try:
                with open(f"sw/build/{app_name}.out", 'r') as f:
                    lines = f.readlines()
            except FileNotFoundError:
                return False

        # Analyse the results of the test
        pattern = re.compile(pattern)  
        for line in lines:
            match = pattern.search(line)
            if match:
                # Extract matched groups dynamically
                matched_data = match.groups()

                # Store results in a generalized way
                result_dict = {output_tags[i]: matched_data[i] for i in range(len(matched_data))}
                break

        # Append to results
        _append_results_to_db(app_name, iteration, result_dict)

    # Dumps the results of the tests up until this point into a result file
    def dump_results(self, filename="results.txt"):
        with open(filename, 'w') as f:
            for result in self.results:
                f.write(result + '\n')
        #TODO: add exception for file mismanagement

    # Performance estimation methods

    def chrono_start(self):
        self.start_time = time.time()
    
    def chrono_stop(self):
        self.end_time = time.time()
        self.it_times.append(self.end_time - self.start_time)
        return self.end_time - self.start_time
    
    def chrono_execution_est(self, loop_size):
        avg_duration = sum(self.it_times) / len(self.it_times)
        remaining_it = loop_size - len(self.it_times)
        remaining_time_raw = remaining_it * avg_duration
        remaining_time = {}
        remaining_time["hours"], remainder = divmod(remaining_time_raw, 3600)
        remaining_time["minutes"], remaining_time["seconds"] = divmod(remainder, 60)
        return remaining_time
    
    # Data generation methods

    # This function generates datasets for every test insered in config.ver.
    # Both input and output datasets are written in a single file, "data.c" and "data.h".
    # The parameters of the test can have a constant value (e.g. datatypes) or a range of values
    # (e.g. sizes of the input, number of channels, order of the FIR filter). 
    # It's possible to define which value give to every single parameter (must be inside indicated range)
    # Otherwise, the values will be chosen randomly.
    import os
import random
import numpy as np

def gen_datasets(self):
    for test in self.cfg.get("test", []):
        test_dir = test["dir"]
        os.makedirs(test_dir, exist_ok=True)

        # Open files for writing
        with open(f"{test_dir}/data.h", 'w') as h_file, open(f"{test_dir}/data.c", 'w') as c_file:
            # Write Header File (data.h)
            h_file.write("#ifndef DATA_H\n")
            h_file.write("#define DATA_H\n\n")
            h_file.write("#include <stdint.h>\n\n")

            # Iterate through parameters list
            if "parameters" in test:
                for param in test["parameters"]:
                    param_name = param["name"]
                    param_value = param["value"]

                    # If the value is a list, take a random value from the range
                    if isinstance(param_value, list):
                        param_value = random.randint(param_value[0], param_value[1])
                        param["value"] = param_value

                    h_file.write(f"#define {param_name} {param_value}\n")

            h_file.write("\n")

            # Iterate through input datasets
            input_datasets = test.get("inputDataset", [])

            # Ensure input_datasets is a list (it might be a dict if only one exists)
            if isinstance(input_datasets, dict):
                input_datasets = [input_datasets]

            # Begin writing C source file (data.c)
            c_file.write('#include "data.h"\n\n')

            input_arrays = []  # Store NumPy input arrays

            for dataset in input_datasets:
                dataset_name = dataset["name"]
                datatype = dataset["dataType"]
                value_range = dataset["valueRange"]
                dimensions = dataset["dimensions"]

                # Convert dimensions to integers (handle parameter references)
                converted_dimensions = []
                for dim in dimensions:
                    if isinstance(dim, str):  # If dimension is parameter-dependent
                        dim = next((p["value"] for p in test["parameters"] if p["name"] == dim), 1)
                    converted_dimensions.append(dim)

                dataset_shape = tuple(converted_dimensions)  # Convert to tuple for NumPy

                # Generate a NumPy array with the correct shape and datatype
                if datatype == "uint8_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.uint8)
                elif datatype == "uint16_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.uint16)
                elif datatype == "uint32_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.uint32)
                elif datatype == "uint64_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.uint64)
                elif datatype == "int8_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.int8)
                elif datatype == "int16_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.int16)
                elif datatype == "int32_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.int32)
                elif datatype == "int64_t":
                    input_array = np.random.randint(value_range[0], value_range[1], size=dataset_shape, dtype=np.int64)
                elif datatype == "float":
                    input_array = np.random.uniform(value_range[0], value_range[1], size=dataset_shape).astype(np.float32)
                elif datatype == "double":
                    input_array = np.random.uniform(value_range[0], value_range[1], size=dataset_shape).astype(np.float64)
                else:
                    raise ValueError(f"unsupported datatype '{datatype}'")

                # Append the NumPy array to the list
                input_arrays.append(input_array)

                # Declare dataset in Header File (data.h)
                total_size = np.prod(dataset_shape)
                h_file.write(f"extern const {datatype} {dataset_name}[{total_size}];\n")

                # Define dataset in Source File (data.c)
                c_file.write(f"const {datatype} {dataset_name}[{total_size}]" + " = {{\n")

                _write_array(c_file, input_array, dataset_shape)

                c_file.write("};\n\n")

            # Generate the golden results using the golden function
            golden_function = test["goldenResultFunction"]["name"]
            try:
                golden_results = _dyn_load_func(golden_function, input_arrays, test["parameters"])
            except Exception as e:
                raise ValueError(f"failed to find golden function '{golden_function}'. Check if it exists in 'functions.py'")

            output_dataset = test.get("outputDataset", [])

            # Write the golden result
            for golden_result in golden_results:
                output_name = output_dataset["name"]
                output_shape = golden_result.shape  # Get NumPy shape
                output_datatype = output_dataset["dataType"]

                # Declare golden result in Header File (data.h)
                total_size = np.prod(output_shape)
                h_file.write(f"extern const {output_datatype} {output_name}[{total_size}];\n")

                # Define golden result in Source File (data.c)
                c_file.write(f"const {output_datatype} {output_name}[{total_size}]" + " = {{\n")

                # Write the golden result array with formatting
                _write_array(c_file, golden_result, output_shape)

                c_file.write("};\n\n")

            # Close Header File
            h_file.write("\n#endif // DATA_H\n")

#__________________________________________________________________________________________________#
# Internal functions

# Write the NumPy array values while keeping proper formatting
def _write_array(f, array, shape, indent=2):
    """
    Writes a NumPy array in a flat C-style format with structured newlines.

    - Uses newlines to visually separate dimensions instead of nested `{}`.
    - The larger the dimension, the more newlines it inserts.

    :param f: File handle to write to.
    :param array: NumPy array to write.
    :param shape: Shape of the array (tuple).
    :param indent: Indentation level.
    :param level: Current depth of recursion.
    """
    
    flat_array = array.flatten()
    num_dims = len(shape)
    
    f.write(" " * indent + "{\n")  # Start of array

    for i, value in enumerate(flat_array):
        # Insert the value
        f.write(f" {value},")

        # Insert a newline after every "row" (last dimension)
        if (i + 1) % shape[-1] == 0:
            f.write("\n" + " " * indent)

        # Insert a **blank line** when finishing a 2D block (2nd-to-last dimension)
        if num_dims >= 2 and (i + 1) % (shape[-2] * shape[-1]) == 0:
            f.write("\n")

        # Insert **two blank lines** when finishing a 3D block
        if num_dims >= 3 and (i + 1) % (shape[-3] * shape[-2] * shape[-1]) == 0:
            f.write("\n\n")

        # Insert **three blank lines** when finishing a 4D block, and so on...
        if num_dims >= 4:
            for d in range(4, num_dims + 1):
                if (i + 1) % np.prod(shape[-d:]) == 0:
                    f.write("\n" * (d - 2))

    f.write("\n" + " " * indent + "};\n")  # End of array

def _load_database():
    """Loads existing database or initializes a new one."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as file:
            return json.load(file)
    return {}  # Return an empty structure if file doesn't exist

def _append_results_to_db(test_name, iteration, results):
    """
    Appends results to the database for a given test application.
    
    :param test_name: The name of the test (e.g., "test1").
    :param iteration: The iteration number.
    :param results: A dictionary of test results (extracted from serial logs).
    """
    db = _load_database()

    # Ensure the test has a list initialized
    if test_name not in db:
        db[test_name] = []

    # Append new result
    result_entry = {"iteration": iteration, **results}
    db[test_name].append(result_entry)

    # Save back to JSON
    with open(DB_FILE, "w") as file:
        json.dump(db, file, indent=4)

# Dynamically load a function from 'functions.py'
def _dyn_load_func(function_name, *args, **kwargs):
    """
    Dynamically imports and executes a function from 'functions.py' in the 'lib' folder.
    """

    module = importlib.import_module("functions") 
    function = getattr(module, function_name)
    return function(*args, **kwargs)
    

# SUPER-IMPORTANT: Every communication by the SW application MUST end with an endword character, which is by default "&".
def _serial_rx_setup(ser, serial_queue, endword="&"):
    try:
        if not ser.is_open:
            raise serial.SerialException("Serial port not open")
        
        received = False
        while not received:
            # Read the data from the serial port
            line = ser.readline().decode('utf-8').rstrip()
            serial_queue.put(line)
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