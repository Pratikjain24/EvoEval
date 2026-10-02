"""Lightweight OpenAI-compatible server for local GGUF models using FastAPI and llama_cpp."""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
from llama_cpp import Llama

DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "models" / "qwen2.5-coder-3b-instruct-q4_k_m.gguf"

app = FastAPI(title="SAGE Local OpenAI-Compatible Server")
llm: Optional[Llama] = None
model_name: str = "qwen2.5-coder-3b-instruct"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False


@app.get("/health")
@app.get("/v1/health")
def health():
    return {"status": "ok", "model": model_name, "loaded": llm is not None}


@app.get("/models")
@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": model_name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
            }
        ],
    }


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest):
    global llm
    if llm is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    start = time.time()
    
    resp = llm.create_chat_completion(
        messages=messages,
        temperature=req.temperature if req.temperature is not None else 0.2,
        top_p=req.top_p if req.top_p is not None else 0.95,
        max_tokens=req.max_tokens or 2048,
    )
    
    # Ensure standard OpenAI format
    resp["model"] = model_name
    return resp


def main():
    global llm, model_name
    parser = argparse.ArgumentParser(description="Serve local GGUF model via OpenAI-compatible API")
    parser.add_argument("--model", type=str, default=str(DEFAULT_MODEL), help="Path to GGUF model")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--threads", type=int, default=8, help="Number of CPU threads (default: 8)")
    parser.add_argument("--ctx", type=int, default=4096, help="Context window size (default: 4096)")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"[ERROR] Model file not found: {model_path}")
        sys.exit(1)

    model_name = model_path.stem
    print(f"Loading GGUF model from {model_path} (threads={args.threads}, ctx={args.ctx})...")
    llm = Llama(
        model_path=str(model_path),
        n_ctx=args.ctx,
        n_threads=args.threads,
        verbose=False,
    )
    print(f"[SUCCESS] Model loaded! Starting OpenAI-compatible server at http://{args.host}:{args.port}/v1")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
