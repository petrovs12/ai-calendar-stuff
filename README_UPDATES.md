# Environment Setup Updates

## Local Environment Setup

This project now uses a local conda environment with Python 3.10 to support CPLEX integration:

1. **Create a local conda environment:**
   ```bash
   conda create --prefix ./py310env python=3.10 -y
   ```

2. **Activate the environment:**
   ```bash
   conda activate ./py310env
   ```
   
   Note: When activated, your prompt will include the environment path:
   ```
   (/path/to/py310env) $
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## CPLEX Integration

For advanced scheduling optimization, this project supports IBM CPLEX Optimizer:

1. **Follow the detailed setup instructions in [CPLEX_SETUP.md](CPLEX_SETUP.md)**

2. **Test your CPLEX installation:**
   ```bash
   python cplex_test.py
   ```

3. **Use CPLEX in your scheduling workflows:**
   The project includes examples of how to leverage CPLEX for optimal scheduling based on calendar constraints.

## Environment Management Tips

- To deactivate the environment: `conda deactivate`
- To remove the environment: `rm -rf ./py310env`
- Always ensure you're using the environment when working on the project 