from fastapi import FastAPI
from .routers.tools import router as tools_router
from .routers.llm import router as llm_router

app = FastAPI()


@app.get('/health')
async def health():
    return {'status': 'ok'}


app.include_router(tools_router)
app.include_router(llm_router)
