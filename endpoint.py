from fastapi import FastAPI, UploadFile, File
from admet import Admet
from pydantic import BaseModel
import asyncio
from asyncio import Queue
import os

class Request(BaseModel):
    smi: str

class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    message: str

QUEUE_COUNT = os.getenv("QUEUE_COUNT", 1);

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
    return model.as_obj()

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

    return outputs

# use rdkit to make mol file
