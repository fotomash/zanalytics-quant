import os
from fastapi import FastAPI, Depends
from .auth import verify_api_key
from .routers.tools import router as tools_router

dependencies = [Depends(verify_api_key)] if os.getenv("MCP2_API_KEY") else []
app = FastAPI(dependencies=dependencies)


@app.get('/health')
async def health():
    return {'status': 'ok'}


app.include_router(tools_router)
