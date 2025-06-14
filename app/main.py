from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.v1 import router_document_generation

app = FastAPI(
    title="DeepChain - Multi-Agent Document Generator",
    version="0.1.0",
    description="An application for generating documents through deep research by a multi-agent system."
)

app.include_router(
    router_document_generation.router,
    prefix="/api/v1",
    tags=["Document Generation"] 
)

@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {"message": "Welcome to the DeepChain Multi-Agent Document Generation API!"}

if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server directly from main.py (for development only)...")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)