# CPLEX Setup for Interview Practice Scheduler

This guide explains how to set up IBM CPLEX Optimizer in the project environment, which is required for advanced scheduling optimization.

## Environment Setup

### 1. Create Python 3.10 Environment

IBM CPLEX requires Python 3.10, so we need to create a compatible environment:

```bash
# Create a local conda environment with Python 3.10
conda create --prefix ./py310env python=3.10 -y

# Activate the environment
conda activate ./py310env

# Install project dependencies
pip install -r requirements.txt
```

### 2. Install CPLEX

If you already have CPLEX Studio installed on your system, you can install the Python API from your local installation:

```bash
# Activate the environment if it's not already activated
conda activate ./py310env

# Navigate to the CPLEX Python API directory for your architecture
# Replace the path below with the location of your CPLEX installation
cd /path/to/CPLEX_Studio/cplex/python/3.10/[your_platform]

# Install the CPLEX Python API
python setup.py install
```

In this project, the CPLEX path used was:
```
/Volumes/vlexar/Applications/CPLEX_Studio2211/cplex/python/3.10/arm64_osx
```

### 3. Verify CPLEX Installation

You can verify that CPLEX and docplex are installed correctly by running:

```bash
python -c "import cplex; print('CPLEX version:', cplex.__version__); import docplex; print('DOcplex version:', docplex.__version__)"
```

You should see output indicating the installed versions of both packages.

### 4. Test CPLEX Optimization

The project includes a simple test script (`cplex_test.py`) that demonstrates CPLEX optimization. Run it with:

```bash
python cplex_test.py
```

If everything is set up correctly, you'll see the solution to a simple linear programming problem.

## Using CPLEX in the Project

Once the setup is complete, the scheduling algorithms in this project can use CPLEX for finding optimal interview practice schedules, considering various constraints like:

- Available time windows
- Duration requirements
- Priority of different practice topics
- Energy level considerations

The `docplex` library provides a high-level interface to CPLEX that makes it easier to model and solve complex optimization problems in Python. 