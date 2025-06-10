from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging

from database import get_session, load_highlighted_memory
from models import Message, HighlightedMemory 
from NPC.utils.openai_client import ask_gpt
from npc_config import get_npc_profile
from prompt_utils import build_system_prompt  # ✅ 새로 추가

router = APIRouter()
logger = logging.getLogger(__name__)

class PlayerResponseRequest(BaseModel):
    npc_id: str
    content: str

@router.post("/npc/respond")
def npc_respond(request: PlayerResponseRequest):
    try:
        session: Session = get_session()

        # 1. 플레이어 발화 저장
        session.add(Message(npc_id=request.npc_id, role="user", content=request.content))
        session.commit()

        # 2. GPT에게 '기억할 만한가?' 판단
        judge_prompt = [
            {"role": "system", "content": (
                "당신은 NPC '영희'의 입장에서 판단합니다. "
                "다음 사용자의 발화가 감정적으로 인상 깊고, 기억에 남을 만한 말인지 판별하세요. "
                "기억할 가치가 있다면 'yes', 아니면 'no'만 대답하세요. "
                "판단 기준은: 감정이 강하게 드러났거나, 자극적이거나, 자기 표현이 뚜렷한 문장입니다."
            )},
            {"role": "user", "content": request.content}
        ]
        verdict = ask_gpt(judge_prompt).strip().lower()
        if verdict == "yes":
            session.add(HighlightedMemory(npc_id=request.npc_id, content=request.content))
            session.commit()

        # 3. 전체 대화 히스토리 불러오기
        result = session.execute(
            select(Message).where(Message.npc_id == request.npc_id).order_by(Message.timestamp)
        )
        messages = result.scalars().all()
        history = [{"role": msg.role, "content": msg.content} for msg in messages]

        # 4. 최근 기억된 발화 3개 불러오기
        highlighted = session.execute(
            select(HighlightedMemory)
            .where(HighlightedMemory.npc_id == request.npc_id)
            .order_by(HighlightedMemory.timestamp.desc())
            .limit(3)
        ).scalars().all()

        memory_lines = ""
        if highlighted:
            memory_lines = "\n".join([f"- {m.content}" for m in highlighted])
            memory_lines = (
                "당신은 아래와 같은 과거의 말을 기억하고 있어요. "
                "하지만 반드시 이 내용을 언급할 필요는 없고, 현재 대화와 관련이 있다면 자연스럽게 반영해도 괜찮습니다.\n"
                f"{memory_lines}\n\n"
            )

        # 5. load_highlighted_memory() 결과 포함
        memory_instruction = ""
        memory = load_highlighted_memory(request.npc_id)
        if memory:
            formatted_memory = "\n".join(f"- {m}" for m in memory[:3])
            memory_instruction = (
                "\n\n다음은 당신이 기억하고 있는 인상 깊은 말들이에요:\n"
                f"{formatted_memory}\n\n"
                "이 기억들은 당신에게 감정적으로 의미가 있었고, "
                "현재 상황에 따라 떠올릴 수도 있고, 무시할 수도 있어요. "
                "꼭 다시 언급하지 않아도 되고, 감정이 격할 땐 이 기억들에 반응해서 말할 수도 있어요. "
                "당신이 판단해서 적절한 방식으로 활용하거나 무시해주세요."
            )

        # 6. system_prompt 구성 (통합 함수)
        system_prompt = build_system_prompt(request.npc_id, memory_lines, memory_instruction)
        gpt_messages = [system_prompt] + history

        # 7. GPT 응답 생성
        npc_reply = ask_gpt(gpt_messages).strip()

        # 8. NPC 응답 저장
        session.add(Message(npc_id=request.npc_id, role="assistant", content=npc_reply))
        session.commit()

        return {"message": "플레이어 응답 저장 및 NPC 반응 생성 완료", "npc_reply": npc_reply}

    except Exception as e:
        logger.error("응답 저장 또는 GPT 오류", exc_info=True)
        return {"error": "응답 저장 또는 GPT 처리 중 오류 발생"}
