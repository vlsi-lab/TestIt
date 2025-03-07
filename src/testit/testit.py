import subprocess
import re
import serial
import pexpect
import threading
import queue
import random
import os
import numpy as np
from . import testit_util
from rich.console import Console
from rich.table import Table
import json
import copy

# Set this to True to enable debugging prints
# TODO: REMOVE BEFORE RELEASE
DEBUG_MODE = False

# TODO: REMOVE BEFORE RELEASE
def PRINT_DEB(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

# This class defines the environment for the verification campaign
class TestItEnv:
    def __init__(self, config):
        self.cfg = config

    def reset_all(self):
        if self.serial_comm_instance.is_open:
          self.serial_comm_instance.close()
        self.serial_comm_instance = None
        self.serial_comm_queue = None
        self.serial_comm_thread = None
        self.gdb = None
        self.project_root = None

    def clear_results(self):
        testit_util._clear_database(self.cfg['report']['dir'])
    
    # Build the model for the simulation tool or the FPGA board
    def build_model(self):
        if self.cfg['target']['type'] == "fpga":
          cmd = f"make fpga-build board={self.cfg['target']['name']}"
          build_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
          if ("ERROR" in build_result.stdout) or ("Error" in build_result.stdout):
              print(build_result.stdout)
              return False
          else:
              return True
        else:
          cmd = f"make sim-build tool={self.cfg['target']['name']}"
          build_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
          if ("ERROR" in build_result.stdout) or ("Error" in build_result.stdout):
              print(build_result.stdout)
              return False
          else:
              return True
    
    # Load the bitstream into the FPGA board
    def load_fpga_model(self):
        cmd = f"make fpga-load board={self.cfg['target']['name']}"
        load_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if ("ERROR" in load_result.stdout) or ("Error" in load_result.stdout):
            print(load_result.stdout)
            return False
        else:
            return True
    
    # Set-up serial communication with the FPGA board
    def serial_begin(self):
        try:
            self.serial_comm_instance = serial.Serial(f"/dev/ttyUSB{self.cfg['target']['usbPort']}", self.cfg['target']['baudrate'], timeout=1)
            
            if not self.serial_comm_instance.is_open:
                return False
        except Exception as e:
            return False
        
        self.serial_comm_queue = queue.Queue()
        
        return True
            
    def setup_deb(self):
        deb_cmd = f"""
        cd {os.getcwd()}
        make deb-setup
        """
        self.deb = pexpect.spawn(f"/bin/bash -c '{deb_cmd}'")
        if self.deb.isalive():
            return True
        else:
            print({self.deb.exitstatus})
            return False
            

    # Set-up GDB
    def setup_gdb(self):
        gdb_cmd = f"""
        cd {os.getcwd()}
        make gdb-setup
        """
        self.gdb = pexpect.spawn(f"/bin/bash -c '{gdb_cmd}'")
        self.gdb.sendline("set pagination off")
        self.gdb.sendline("set confirm off")
        self.gdb.expect('(gdb)')
        self.gdb.sendline('set remotetimeout 2000')
        self.gdb.expect('(gdb)')
        self.gdb.sendline('target extended-remote localhost:3333')
        self.gdb.expect('(gdb)')

        if self.gdb.isalive():
            PRINT_DEB("GDB process is still running.")
            return True
        else:
            PRINT_DEB("GDB process has terminated.")
            if self.gdb.exitstatus is not None:
                print(f"GDB exit status: {self.gdb.exitstatus}")
            if self.gdb.signalstatus is not None:
                print(f"GDB terminated by signal: {self.gdb.signalstatus}")
            exit(1)
            
    # Stop GDB
    def stop_gdb(self):
        self.gdb.sendcontrol('c')
        self.gdb.terminate()
    
    def stop_deb(self):
        self.deb.sendcontrol('c')
        self.deb.terminate()

    # Launch a test by compiling the target application and loading it into the FPGA flash via GDB
    def launch_test(self, app_name, iteration, pattern=r'(\d+):(\d+):(\d+)', output_tags=None, timeout_t=0):
        
        if output_tags is None:
            output_tags = ["ID", "Cycles", "Outcome"]

        # Test using the FPGA board
        if self.cfg['target']['type'] == "fpga":
            # Check that the serial connection is still open
            if not self.serial_comm_instance.is_open:
                print("ERROR: Serial port is not open!")
                exit(1) 
            self.serial_comm_thread = threading.Thread(target=testit_util._serial_rx_setup, args=(self.serial_comm_instance, self.serial_comm_queue))

            self.serial_comm_thread.start()

            # Compile the application
            app_compile_cmd = f"make sw-fpga app={app_name} target={self.cfg['target']['name']}"
            result_compilation = subprocess.run(app_compile_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_compilation.stdout) or ("Error" in result_compilation.stdout) or ("error" in result_compilation.stdout) or \
              ("ERROR" in result_compilation.stderr) or ("Error" in result_compilation.stderr) or ("error" in result_compilation.stderr):
              with open("testit_crash.log", "w") as file:
                    file.write(result_compilation.stdout)
                    file.write(result_compilation.stderr)
              return False
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

            exit_detected = False
            while not exit_detected:
                try:
                    index = self.gdb.expect([r"Breakpoint", pexpect.TIMEOUT], timeout=10)
                    if index == 0:
                        exit_detected = True
                        PRINT_DEB("Program finished execution.")
                except pexpect.exceptions.EOF:
                    break
            
            # Wait for serial to finish
            self.serial_comm_thread.join()
            
            outputLines = []
            while not self.serial_comm_queue.empty():
                outputLines.append(self.serial_comm_queue.get())
        
        # Test using the simulation tool
        else:
            # Compile the application
            app_compile_cmd = f"make sw-sim app={app_name}"
            result_compilation = subprocess.run(app_compile_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_compilation.stdout) or ("Error" in result_compilation.stdout) or ("error" in result_compilation.stdout) or \
              ("ERROR" in result_compilation.stderr) or ("Error" in result_compilation.stderr) or ("error" in result_compilation.stderr):
              with open("testit_crash.log", "w") as file:
                    file.write(result_compilation.stdout)
                    file.write(result_compilation.stderr)
              return False
            
            PRINT_DEB("Compilation successful!")

            # Launch the simulation test
            sim_cmd = f"make sim-run app={app_name}"
            result_sim = subprocess.run(sim_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_sim.stdout) or ("Error" in result_sim.stdout) or ("error" in result_sim.stdout) or \
              ("ERROR" in result_sim.stderr) or ("Error" in result_sim.stderr) or ("error" in result_sim.stderr):
                with open("testit_crash.log", "w") as file:
                    file.write(result_sim.stdout)
                    file.write(result_sim.stderr)
                return False
            
            PRINT_DEB("Simulation successful!")

            # Read the output file
            try:
                with open(self.cfg['target']['outputFile'], 'r') as f:
                    outputLines = f.readlines()
            except FileNotFoundError:
                return False
        
        PRINT_DEB("Output lines:", outputLines)

        # Analyse the results of the test
        output_matches = []
        pattern = re.compile(pattern)  
        for line in outputLines:
            match = pattern.search(line)
            if match:
                
                matched_data = match.groups()
                result_dict = {output_tags[i]: matched_data[i] for i in range(len(matched_data))}
                output_matches.append(result_dict)
                
        testit_util._append_results_to_report(self.cfg['report']['dir'], app_name, iteration, output_matches)
        return True

    # Generate a report of the last verification campaign.
    def gen_report(self, sort_key=None, ascending=True):
        console = Console(record=True)

        with open(f"{self.cfg['report']['dir']}/test_results.json", "r") as f:
            results = json.load(f)

        for test_name, iterations in results.items():
           
            table = Table(title=f"Test Report: {test_name}")

            if iterations:
                for key in iterations[0].keys():
                    table.add_column(key, style="cyan")

                if sort_key and sort_key in iterations[0]:
                    try:
                        # Try numeric sorting first
                        iterations.sort(key=lambda x: int(x[sort_key]), reverse=not ascending)
                    except ValueError:
                        # Fallback to string sorting
                        iterations.sort(key=lambda x: x[sort_key], reverse=not ascending)

            for entry in iterations:
                table.add_row(*[str(entry[key]) for key in entry])

            console.print(table)

        with open(f"{self.cfg['report']['dir']}/report.rpt", "w") as f:
            f.write(console.export_text())
    
    # This function generates datasets for every test insered in config.test.
    # Both input and output datasets are written in a single file, "data.c" and "data.h".
    def gen_datasets(self, sweep_mode=False, test_iteration=None):
        testCopy = copy.deepcopy(self.cfg.get("tests", []))
        for test in testCopy:
            
            test_dir = test["dir"]
            if not os.path.exists(test_dir):
                print(f"ERROR: Test directory '{test_dir}' not found.")
                return False

            # Open files for writing
            try:
                with open(f"{test_dir}/{test['genFilesName']}.h", 'w') as h_file, open(f"{test_dir}/{test['genFilesName']}.c", 'w') as c_file:
                    
                    h_file.write("#ifndef TEST_DATA_H\n")
                    h_file.write("#define TEST_DATA_H\n\n")
                    h_file.write("#include <stdint.h>\n\n")

                    # Iterate through parameters list
                    if "parameters" in test:
                        if sweep_mode:
                            sweep_parameters = testit_util._get_sweep_parameters(test_iteration, test['parameters'])
                       
                        parameter_index = 0
                        for param in test['parameters']:
                            
                            param_name = param["name"]

                            if not sweep_mode:
                                
                                # If the parameter's value is a list, take a random value from the range
                                if isinstance(param["value"], list):
                                    param_value = random.randint(param["value"][0], param["value"][1])
                                    param["value"] = param_value
                            else:
                                param["value"] = sweep_parameters[parameter_index]
                                parameter_index += 1

                            param_value = param["value"]
                            h_file.write(f"#define {param_name} {param_value}\n")

                    h_file.write("\n")

                    file_name = test['genFilesName']
                    c_file.write(f'#include "{file_name}.h"\n\n')

                    input_datasets = test.get("inputDataset", [])

                    # Ensure input_datasets is a list (it might be a dict if only one exists)
                    if isinstance(input_datasets, dict):
                        input_datasets = [input_datasets]
                        
                    if input_datasets:
                        
                        input_arrays = []
                        
                        for dataset in input_datasets:
                            dataset_name = dataset["name"]
                            datatype = dataset["dataType"]
                            value_range = dataset["valueRange"]
                            dimensions = dataset["dimensions"]

                            # Handle parameter-dependent dimensions
                            converted_dimensions = []
                            for dim in dimensions:
                                if isinstance(dim, str):
                                    dim = next((p["value"] for p in test['parameters'] if p["name"] == dim), 1)
                                converted_dimensions.append(dim)

                            dataset_shape = tuple(converted_dimensions)

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

                            input_arrays.append(input_array)

                            total_size = np.prod(dataset_shape)
                            h_file.write(f"extern const {datatype} {dataset_name}[{total_size}];\n")

                            # Define dataset in Source File (data.c)
                            c_file.write(f"const {datatype} {dataset_name}[{total_size}]" + " = {\n")
                            
                            # Write the golden result array with formatting
                            testit_util._write_array(c_file, input_array, dataset_shape)

                            c_file.write("};\n\n")

                    output_datasets = test.get("outputDataset", [])

                    # Ensure output_datasets is a list (it might be a dict if only one exists)
                    if isinstance(output_datasets, dict):
                        output_datasets = [output_datasets]
                    
                    # Output datasets are not mandatory
                    if output_datasets:
                        # Generate the golden results using the golden function
                        golden_function = testit_util._dyn_load_func(test["goldenResultFunction"]["name"])
                        golden_results = golden_function(input_arrays, test["parameters"])

                        # Ensure golden_results is a list (it might be a single array)
                        if testit_util._is_numpy_array(golden_results):
                            golden_results = [golden_results]

                        # Write the golden result
                        for iteration, golden_result in enumerate(golden_results):
                            output_name = output_datasets[iteration]["name"]
                            output_shape = golden_result.shape
                            output_datatype = output_datasets[iteration]["dataType"]

                            total_size = np.prod(output_shape)
                            h_file.write(f"extern const {output_datatype} {output_name}[{total_size}];\n")

                            c_file.write(f"const {output_datatype} {output_name}[{total_size}]" + " = {\n")

                            # Write the golden result array with formatting
                            testit_util._write_array(c_file, golden_result, output_shape)

                            c_file.write("};\n\n")

                    # Close Header File
                    h_file.write("\n#endif // TEST_DATA_H\n")
            except Exception as e:
                print(f"ERROR: {e}")
                return False
        
        return True