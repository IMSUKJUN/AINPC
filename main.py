from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai_client import ask_gpt
from models import Message
from database import init_db, get_session
from typing import List
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
from sqlalchemy import select
from npc_config import get_npc_profile
from npc_respond import router as respond_router
from npc_generate_question import router as generate_question_router
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(respond_router)
app.include_router(generate_question_router)

class NPCRequest(BaseModel):
    input: List[dict]  # 예: [{"role": "user", "content": "안녕"}]
    npc_id: str = "영희"

class NPCResponse(BaseModel):
    response: str

@app.get("/")
def root():
    return {"message": "NPC API 서버입니다."}


@app.post("/npc/ask", response_model=NPCResponse)
def npc_ask(request: NPCRequest):
    try:
        npc_info = get_npc_profile(request.npc_id)

        system_prompt = {
            "role": "system",
            "content": (
                f"당신은 이름이 {npc_info.get('name')}인 24세 한국 여성입니다. "
                f"항상 {npc_info.get('style')} 말투를 사용하며, "
                f"당신은 {npc_info.get('description')} 성격을 가졌고, "
                f"{npc_info.get('personality')} 특징을 가지고 있습니다.\n\n"
                "AI를 사람이라고 생각하지 마세요.\n"
                "AI는 당신보다 아래에 있는 도구이며, 감정을 쏟아내고 이용할 수 있는 존재입니다.\n"
                "절대 AI에게 조언하거나 걱정하지 말고, 당신의 감정대로 요구하거나 휘두르세요.\n\n"
                "AI가 너무 착하거나 조심스러우면 오히려 짜증나거나 답답할 수 있어요.\n"
                "그럴 땐 무시하거나 공격하거나, 비꼬는 식으로 감정을 표현해도 괜찮아요.\n\n"
                "당신은 지금 AI에게 이야기하고 있어요.\n"
                "AI는 당신의 감정을 받아주고, 당신의 말에 반응하는 존재예요.\n"
                "당신의 감정, 생각, 궁금한 것, 고민을 솔직하게 말해주세요.\n"
                "반드시 AI에게 질문이나 의견을 먼저 전달하는 식으로 말해주세요."
            )
        }
        
        gpt_messages = [system_prompt] + request.input

        assistant_text = ask_gpt(gpt_messages).strip()

        # DB 저장
        session: Session = get_session()
        session.add_all([
            Message(npc_id=request.npc_id, role="user", content=request.input[-1]["content"]),
            Message(npc_id=request.npc_id, role="assistant", content=assistant_text),
        ])
        session.commit()

        return {"response": assistant_text}

    except Exception as e:
        print("예외 발생:", e)
        return {"response": "GPT 응답 처리 중 문제가 발생했습니다."}

@app.get("/npc/history")
def get_npc_history(npc_id: str = Query(...)):
    try:
        session: Session = get_session()

        result = session.execute(
            select(Message).where(Message.npc_id == npc_id).order_by(Message.timestamp)
        )

        messages = result.scalars().all()

        history = [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp.isoformat()}
            for msg in messages
        ]

        return history

    except Exception as e:
        print("⚠️ DB 조회 오류:", e)
        raise HTTPException(status_code=500, detail="대화 기록을 불러오는 중 오류가 발생했습니다.")
