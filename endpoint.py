from fastapi import FastAPI, UploadFile, File
from admet import Admet, Admet_Return
from pydantic import BaseModel
import asyncio
from asyncio import Queue
import os
from typing import List, Optional

class Request(BaseModel):
    smi: str

class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    message: str

class Response(BaseModel):
    """Response model for SMILES prediction endpoint."""
    smiles: str
    status: str
    results: Admet_Return
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

@app.post("/smi/")
async def smi_request(req: Request):
    model = await model_pool.get()
    try:
        model.run(req.smi);
    finally:
        await model_pool.put(model)
    return Response(
        smiles=req.smi,
        status="success",
        results=model.as_obj()
    )

@app.post("/upload_smi/")
async def upload_smi(file: UploadFile = File(...)):
    contents = (await file.read()).decode()
    smiles_list = [line.strip() for line in contents.splitlines() if line.strip()]

    outputs = []
    model = await model_pool.get()
    try:
        for smi in smiles_list:
            model.run(smi)
            outputs.append(model.as_obj())
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