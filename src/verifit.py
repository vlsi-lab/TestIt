import subprocess
import re
import serial
import pexpect
import threading
import queue
import random
import os
import numpy as np
from verifit_util import _write_array, _load_database, _clear_database, _append_results_to_report, _serial_rx_setup, _dyn_load_func

# Set this to True to enable debugging prints
# TODO: REMOVE BEFORE RELEASE
DEBUG_MODE = False

# TODO: REMOVE BEFORE RELEASE
def PRINT_DEB(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

# This class defines the environment for the verification campaign
class VerifItEnv:
    def __init__(self, config):
        self.cfg = config
        self.results = []
        self.it_times = []
        _clear_database()

    def reset_all(self):
        self.results = []
        self.it_times = []
        if self.serial_comm_instance.is_open:
          self.serial_comm_instance.close()
        self.serial_comm_instance = None
        self.serial_comm_queue = None
        self.serial_comm_thread = None
        self.gdb = None
        self.project_root = None

    def clear_results(self):
        self.results = []
    
    # Build the model for the simulation tool or the FPGA board, inlcuding the synthesis if needed
    def build_model(self, fpga_synthesized=True):
        if self.cfg['target']['type'] == "fpga":
          if fpga_synthesized:
            cmd = f"make fpga-build board={self.cfg['target']['name']}"
            subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if ("ERROR" in cmd.stderr) or ("Error" in cmd.stderr):
                print(cmd.stderr)
                return False
            else:
                return True
        else:
          cmd = f"make sim-build tool={self.cfg['target']['name']}"
          subprocess.run(cmd, shell=True, capture_output=True, text=True)
          if ("ERROR" in cmd.stderr) or ("Error" in cmd.stderr):
              print(cmd.stderr)
              return False
          else:
              return True
    
    # Load the bitstream into the FPGA board
    def load_fpga_model(self):
        cmd = f"make fpga-load board={self.cfg['target']['name']}"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if ("ERROR" in cmd.stderr) or ("Error" in cmd.stderr):
            print(cmd.stderr)
            return False
        else:
            return True
    
    # Set-up serial communication with the FPGA board
    def serial_begin(self):
        try:
            self.serial_comm_instance = serial.Serial(self.cfg['target']['usbPort'], self.cfg['target']['baudrate'], timeout=1)
            self.serial_comm_queue = queue.Queue()
            self.serial_comm_thread = threading.Thread(target=_serial_rx_setup, args=(self.ser, self.serial_comm_queue))
            
            if self.serial_comm_instance.is_open:
                return True
            else:
                return False
        except Exception as e:
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
    def launch_test(self, app_name, iteration, pattern=r'(\d+):(\d+):(\d+)', output_tags=None, timeout_t=0):
        
        if output_tags is None:
            output_tags = ["ID", "Cycles", "Outcome"]

        # Test using the FPGA board
        if self.cfg['target']['type'] == "fpga":

            if not self.serial_comm_instance.is_open:
                print("ERROR: Serial port is not open!")
                exit(1) 

            self.serial_comm_thread.start()

            # Compile the application
            app_compile_cmd = f"make sw app={app_name}"
            result_compilation = subprocess.run(app_compile_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_compilation.stderr) or ("Error" in result_compilation.stderr):
                print(result_compilation.stderr)
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
            try:
              self.gdb.expect('Breakpoint', timeout=timeout_t)
            except pexpect.TIMEOUT:
              PRINT_DEB("Timeout reached.")
              self.gdb.terminate()
              return False
            
            # Wait for serial to finish
            self.serial_comm_thread.join()
            
            outputLines = []
            while not self.serial_comm_queue.empty():
                outputLines.append(self.serial_comm_queue.get())
        
        # Test using the simulation tool
        else:
            # Compile the application
            app_compile_cmd = f"make sw app={app_name}"
            result_compilation = subprocess.run(app_compile_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_compilation.stderr) or ("Error" in result_compilation.stderr):
                print(result_compilation.stderr)
                return False
            
            PRINT_DEB("Compilation successful!")

            # Launch the simulation test
            sim_cmd = f"make sim-run app={app_name}"
            result_sim = subprocess.run(sim_cmd, shell=True, capture_output=True, text=True)

            if ("ERROR" in result_sim.stderr) or ("Error" in result_sim.stderr):
                print(result_sim.stderr)
                return False
            
            PRINT_DEB("Simulation successful!")

            # Read the output file
            try:
                with open(f"sw/build/{app_name}.out", 'r') as f:
                    outputLines = f.readlines()
            except FileNotFoundError:
                return False

        # Analyse the results of the test
        pattern = re.compile(pattern)  
        for line in outputLines:
            match = pattern.search(line)
            if match:
                
                matched_data = match.groups()
                result_dict = {output_tags[i]: matched_data[i] for i in range(len(matched_data))}
                break

        _append_results_to_report(app_name, iteration, result_dict)

    # Dumps the results of the tests up until this point into a result file
    def dump_results(self, filename="results.txt"):
        with open(filename, 'w') as f:
            for result in self.results:
                f.write(result + '\n')
        #TODO: add exception for file mismanagement
    
    # This function generates datasets for every test insered in config.ver.
    # Both input and output datasets are written in a single file, "data.c" and "data.h".
    def gen_datasets(self):
        for test in self.cfg.get("test", []):
            test_dir = test["dir"]
            os.makedirs(test_dir, exist_ok=True)

            # Open files for writing
            with open(f"{test_dir}/data.h", 'w') as h_file, open(f"{test_dir}/data.c", 'w') as c_file:
                
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

                input_datasets = test.get("inputDataset", [])

                # Ensure input_datasets is a list (it might be a dict if only one exists)
                if isinstance(input_datasets, dict):
                    input_datasets = [input_datasets]

                c_file.write('#include "data.h"\n\n')

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
                            dim = next((p["value"] for p in test["parameters"] if p["name"] == dim), 1)
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
                    c_file.write(f"const {datatype} {dataset_name}[{total_size}]" + " = {{\n")
                    
                    # Write the golden result array with formatting
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
                    output_shape = golden_result.shape
                    output_datatype = output_dataset["dataType"]

                    total_size = np.prod(output_shape)
                    h_file.write(f"extern const {output_datatype} {output_name}[{total_size}];\n")

                    c_file.write(f"const {output_datatype} {output_name}[{total_size}]" + " = {{\n")

                    # Write the golden result array with formatting
                    _write_array(c_file, golden_result, output_shape)

                    c_file.write("};\n\n")

                # Close Header File
                h_file.write("\n#endif // DATA_H\n")
