# Just TestIt!

TestIt is a python package designed to **automate full-system integration testing** using a **Software-Based Self-Test (SBST)** approach.
While formal verification methods are highly effective for targeting individual components, their complexity grows exponentially with the size of the System-Under-Test (SUT), making them impractical for testing large scale systems, like MCUs.
Furthermore, they do not test interactions between the hardware platform and the software stack, which is essential for validating real-world functionality.
Last but not least, they are limited to simulated environments, with all their limitations. 

TestIt tackles these limitations and to **bridge the gap** between **formal verification** and **real-world applications**.

#### In short, what can TestIt do?
- Automate **generation** of **random datasets** and **reference values**, according to your specifications.
- Automate **building** of simulation **models** and synthesis for FPGA.
- Automate **compilation** of SW application, which take advantage of the datasets it generates.
- Automate **execution of tests**, both in simulation environments and using FPGAs, which greatly speed up the test time (up to **x11 times reduction**).
- Characterize the **real-world performance** of your system.

#### How can TestIt do all of this? 
With just three requirements:
- A simple **configuration file**, `config.test`, in which you have to describe both *your workflow* and the *tests* you want to run.
- A **python module**, `testit_golden.py`, in which you can develop the *golden functions* used to generate the reference values for your test.
- A complete **Makefile-based workflow**, with some custom targets, as described below. This is the *gateway* that TestIt uses to access your workflow to build, compile and load.

#### How can you use TestIt?
Again, very simple! Just go to TestIt's documentation at https://vlsi-lab.github.io/TestIt/.
If you have any question or suggestions, just contact Tommaso Terzano at tommaso.terzano@gmail.com.
He will be glad to connect with you and help you with any doubt you might have.

## Installation

Simply run this command in your bash terminal:

```bash
pip install testitpy
```

That's it!

## Usage

```bash
$ testit -h

usage: testit [-h] {run,setup,report} ...

TestIt CLI tool

positional arguments:
  {run,setup,report}
    run               Run the verification process
    setup             Set up the verification environment
    report            Generate a report based on the test results

options:
  -h, --help          show this help message and exit
```

[![Publish Python 🐍 distribution 📦 to PyPI and TestPyPI](https://github.com/vlsi-lab/TestIt/actions/workflows/release.yml/badge.svg)](https://github.com/vlsi-lab/TestIt/actions/workflows/release.yml)

[![Downloads](https://img.shields.io/badge/dynamic/json.svg?label=downloads&url=https%3A%2F%2Fpypistats.org%2Fapi%2Fpackages%2Ftestitpy%2Frecent&query=data.last_month&colorB=brightgreen&suffix=%2FMonth)](https://pypistats.org/packages/testitpy)  [![PyPi package](https://img.shields.io/badge/PyPi%20package-blue?style=flat&logo=https://pypi.org/static/images/logo-small.8998e9d1.svg&link=https://pypi.org/project/testitpy/)](https://pypi.org/project/testitpy/)  [![gitHub](https://img.shields.io/badge/gitHub-green?style=flat&link=https://github.com/vlsi-lab/TestIt)](https://github.com/vlsi-lab/TestIt)

---

