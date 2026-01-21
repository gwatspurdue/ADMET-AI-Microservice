# ADMET-AI Microservice

A FastAPI microservice for predicting ADME properties of drug-like compounds from SMILES strings.

## Setup

### Prerequisites
- Python 3.10+ (see [environment.yml](environment.yml))
- Conda or Mamba

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/ADMET-AI-Microservice.git
cd ADMET-AI-Microservice
```

2. Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate admet_api
```

## Option: Using Singularity / Apptainer

Build the container from the included definition file:
```bash
singularity build admet_ai.sif admet_ai.def
```

Run the container. The container defines EXPOSE=8000 by default; to override the exposed port set the EXPOSE environment variable when running the container:
```bash
singularity exec --env EXPOSE=8001 admet_ai.sif
```

Inside the container the entrypoint will start the FastAPI server and bind to 0.0.0.0 on the port given by EXPOSE.

## Running the API Locally

Start the FastAPI server with uvicorn (recommended for local development):
```bash
EXPOSE=8000 python3 -m uvicorn endpoint:app --host 0.0.0.0 --port "$EXPOSE" --reload
```

The API will be available at http://localhost:8000 (or the value of EXPOSE).

Open the interactive docs at http://localhost:8000/docs.

## API Endpoints

### GET `/health`
Returns the health of the endpoint.

### POST `/smi/`
Predict ADME properties for a single SMILES string. Request body:
```json
{
  "smi": "CCO"
}
```

### POST `/upload_smi/`
Upload a plain text file containing one SMILES per line. Example using curl:
```bash
curl -F "file=@compounds.txt" localhost:8000/upload_smi/
```

## Available Properties
The service returns a large set of ADME/toxicity properties (see `admet.py` -> `ALL_PROPS` for the full list). Example categories include:

- Physico-chemical: `molecular_weight`, `logP`, `tpsa`, `QED`
- Absorption: `HIA_Hou`, `Caco2_Wang`, `Solubility_AqSolDB`
- Distribution: `BBB_Martins`, `PPBR_AZ`, `VDss_Lombardo`
- Metabolism: multiple `CYP*` inhibition/substrate predictions
- Excretion: `Half_Life_Obach`, `Clearance_Hepatocyte_AZ`
- Toxicity: `hERG`, `AMES`, `ClinTox`, `LD50_Zhu`

For the authoritative list see [admet.py](admet.py).

## Project Structure

```
├── admet.py                  # ADMET model wrapper and property list
├── endpoint.py               # FastAPI application and routes
├── admet_ai.def              # Singularity/Apptainer definition
├── environment.yml           # Conda environment specification
├── entrypoint.sh             # Container entrypoint (uses EXPOSE)
└── README.md                 # This file
```
