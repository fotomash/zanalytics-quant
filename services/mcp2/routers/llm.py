import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..auth import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])


class WhisperRequest(BaseModel):
    question: str


class WhisperResponse(BaseModel):
    response: str


@router.post('/llm/whisperer', response_model=WhisperResponse)
async def whisperer(req: WhisperRequest) -> WhisperResponse:
    api_key = os.getenv('LLM_API_KEY')
    template = os.getenv('WHISPER_PROMPT_TEMPLATE')
    if not api_key or not template:
        raise HTTPException(status_code=503, detail='LLM not configured')

    prompt = template.format(question=req.question)
    url = os.getenv('LLM_API_URL', 'https://api.openai.com/v1/chat/completions')
    model = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')

    headers = {'Authorization': f'Bearer {api_key}'}
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    content = data['choices'][0]['message']['content'].strip()
    return WhisperResponse(response=content)
