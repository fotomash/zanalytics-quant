from fastapi import FastAPI
from .routers.tools import router as tools_router
from .routers.streams import router as streams_router

app = FastAPI()


@app.get('/health')
async def health():
    return {'status': 'ok'}


app.include_router(tools_router)
app.include_router(streams_router)
