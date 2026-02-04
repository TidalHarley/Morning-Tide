"""
AI Tides - 轻量反馈服务
用于接收前端反馈并落盘到 JSON
"""
from datetime import datetime
from typing import List, Optional
import json
import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .config import config

app = FastAPI(title="AI Tides Feedback API")


class FeedbackItem(BaseModel):
    id: str
    contentType: str
    vote: str
    title: str
    url: Optional[str] = None
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    createdAt: Optional[str] = None
    clientId: Optional[str] = None


def _load_feedback(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_feedback(path: str, data: List[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.post("/feedback")
def post_feedback(item: FeedbackItem):
    payload = item.model_dump()
    payload["receivedAt"] = datetime.utcnow().isoformat() + "Z"
    path = config.feedback_path
    history = _load_feedback(path)
    history.append(payload)
    _save_feedback(path, history)
    return {"status": "ok", "count": len(history)}


@app.get("/feedback")
def get_feedback(limit: int = 100):
    path = config.feedback_path
    history = _load_feedback(path)
    return {"count": len(history), "items": history[-limit:]}
