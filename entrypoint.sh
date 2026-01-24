#!/bin/bash

# Activate the conda environment
source /environment.sh
conda activate admet_api

# Run the app through fastapi to expose the ports
fastapi dev /code/endpoint.py --host 0.0.0.0 --port "$PORT"


#example of working apptainer commands-> 
#single SMILE str: apptainer run admet_ai.sif -smi "CCO"
#list of SMILEs str: apptainer run admet_ai.sif -list /path/to/smiles_list.txt
#This file will eventually have to changed to make this object image easier and more useful for other scripts, like MOO prediction scripts
