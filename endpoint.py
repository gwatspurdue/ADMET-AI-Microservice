from fastapi import FastAPI, UploadFile, File
from admet import Admet, Admet_Return, ALL_PROPS
from pydantic import BaseModel
import asyncio
from asyncio import Queue
import os
from typing import Dict, List, Optional

class Request(BaseModel):
    smiles: str
    property: Optional[List[str]] = None

class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    message: str

class PropertyResult(BaseModel):
    """Prediction result for a single property."""
    property: str
    status: str
    results: Optional[float] = None
    error: Optional[str] = None

class Response(BaseModel):
    """Response model for SMILES prediction endpoint."""
    smiles: str
    status: str
    results: Dict[str, PropertyResult]
    errors: Optional[str] = None

class BulkResponse(BaseModel):
    """Response model for bulk SMILES prediction endpoint."""
    filename: str
    requested_properties: Optional[List[str]] = None
    total_smiles: int
    results: List[Response]

QUEUE_COUNT = int(os.getenv("QUEUE_COUNT", 1));

app = FastAPI()
model_pool: Queue #keep model usage thread safe with a queue

@app.on_event("startup")
async def start():
    global model_pool
    model_pool = Queue()
    for _ in range(QUEUE_COUNT):
        model_pool.put_nowait(Admet())

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service status
    """
    return HealthResponse(
        status="healthy",
        message="ADMEThyst microservice is running"
    )

@app.post("/smi")
async def smi_request(req: Request):
    model = await model_pool.get()
    properties_to_use = req.property if req.property else [prop[0] for prop in ALL_PROPS]
    try:
        model.run(req.smiles)
        results = {}
        for prop in properties_to_use:
            try:
                results[prop] = PropertyResult(
                    property=prop,
                    status="success",
                    results=model.__getattr__(f'get_{prop}')()
                )
            except Exception as e:
                results[prop] = PropertyResult(
                    property=prop,
                    status="error",
                    error=str(e)
                )
        return Response(smiles=req.smiles, status='success', results=results)
    finally:
        await model_pool.put(model)

@app.post("/upload_smi")
async def upload_smi(file: UploadFile = File(...), property: Optional[List[str]] = None):
    contents = (await file.read()).decode()
    smiles_list = [line.strip() for line in contents.splitlines() if line.strip()]

    outputs = []
    model = await model_pool.get()
    properties_to_use = property if property else [prop[0] for prop in ALL_PROPS]
    try:
        for smi in smiles_list:
            model.run(smi)
            results = {}
            for prop in properties_to_use:
                try:
                    results[prop] = PropertyResult(
                        property=prop,
                        status="success",
                        results=model.__getattr__(f'get_{prop}')()
                    )
                except Exception as e:
                    results[prop] = PropertyResult(
                        property=prop,
                        status="error",
                        error=str(e)
                    )
        outputs.append(results)
    finally:
        await model_pool.put(model)

    return BulkResponse(
        filename=file.filename,
        requested_properties=smiles_list,
        total_smiles=len(smiles_list),
        results=[
            Response(
                smiles=smi,
                status="success",
                results=output
            ) for smi, output in zip(smiles_list, outputs)
        ]
    )