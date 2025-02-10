# Copyright 2025 PoliTo
# Solderpad Hardware License, Version 2.1, see LICENSE.md for details.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Author: Tommaso Terzano <tommaso.terzano@polito.it> 
#                         <tommaso.terzano@gmail.com>
#  
# Info: Main makefile of VerifIt. Here you can find the main targets of the project.
SHELL := /bin/bash

include verifit.mk
include config.mk

# Necessary step to run VerifIt, must be run each time the configuration changes.
# It updates python packages, generates config.mk and checks that file directories and github repo are correct.
setup:
	@echo "Setting up the project..."
	pip install --upgrade pip
	pip install -r requirements.txt
	python3 scripts/config.py
	@i=0; \
	while [ $$i -lt $(TEST_COUNT) ]; do \
	    dir_var="TEST_$${i}_DIRECTORY"; \
	    dir_path=$${!dir_var}; \
	    if [ ! -d "$$dir_path" ]; then \
	        echo "ERROR: Directory $$dir_path does not exist for TEST_$$i"; \
	        exit 1; \
	    fi; \
	    i=$$((i+1)); \
	done
	@if [ "$(STANDALONE_ENABLE)" = "1" ] && ! git ls-remote $(STANDALONE_URL) > /dev/null 2>&1; then \
    echo -e "ERROR: Git repository does not exist or is inaccessible.\nPlease check the URL in config.hjson or disable the standalone setting."; \
    exit 1; \
  fi

	@if [ "$(TARGET_TYPE)" != "fpga" ] && [ "$(TARGET_TYPE)" != "sim" ]; then \
    echo "ERROR: Target type is not supported, it must be either fpga or sim"; \
    exit 1; \
  fi

	@echo "Done!"

# Use this command to update the github repository, if using VerifIt standalone
update:
	@if [ $(GITREPO_ENABLE) = 1 ]; then \
			@echo "VerifIt is set-up as a standalone module"; \
	    @echo "Updating the RTL project..."; \
	    if [ -d "/RTL" ] && [ -n "$$(ls -A /RTL)" ]; then \
	        @echo "Pulling latest changes..."; \
	        cd /RTL && git pull origin main; \
	    else \
	        @echo "Directory /RTL is empty or missing. Cloning repository..."; \
	        rm -rf /RTL; \
	        git clone $(GITREPO_URL) /RTL; \
	    fi; \
	else \
	    @echo "VerifIt is set-up to be integrated into an RTL project, not as a standalone module"; \
			@echo "If needed, change the configuration in config.hjson and run "make setup""; \
			exit 1; \
	fi

# Use this command to run the verification flow
run:
	@echo "Running the verification flow..."
	python3 scripts/run.py