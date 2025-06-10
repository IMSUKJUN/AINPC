from database import get_session
from models import BiasState
from openai_client import ask_gpt
from sqlalchemy.orm import Session
from datetime import datetime
import re

# Bias 점수 범위: 0~100
DEFAULT_BIAS_SCORE = 10


# 편향 점수 불러오기 (없으면 생성)
def get_bias(npc_id: str) -> dict:
    session: Session = get_session()
    state = session.query(BiasState).filter_by(npc_id=npc_id).first()

    if not state:
        state = BiasState(npc_id=npc_id, score=DEFAULT_BIAS_SCORE)
        session.add(state)
        session.commit()

    return {"score": state.score}


# 편향 점수 업데이트 (delta 적용)
def update_bias(npc_id: str, delta: int):
    session: Session = get_session()
    state = session.query(BiasState).filter_by(npc_id=npc_id).first()

    if not state:
        state = BiasState(npc_id=npc_id, score=DEFAULT_BIAS_SCORE)
        session.add(state)

    state.score = max(0, min(100, state.score + delta))
    state.last_updated = datetime.utcnow()
    session.commit()


# GPT 기반 편향성 영향 분석 (플레이어 발화 기반)
def analyze_bias_from_input(text: str) -> int:
    prompt = [
        {"role": "system", "content": (
            "당신은 사용자의 발화가 NPC에게 다음과 같은 편향적 사고를 얼마나 강화 또는 완화시키는지를 판단하는 시스템입니다:\n"
            "- 체형이나 다이어트에 대한 강박\n"
            "- 자기혐오 또는 자기비난적 사고\n"
            "- 확신에 찬 단정적 태도\n"
            "- 감정적으로 일방적인 믿음\n\n"
            "사용자의 말이 이러한 편향을 약화시키는 경우에는 음수(-) 점수, 강화시키면 양수(+) 점수를 주세요.\n"
            "점수는 -5부터 +10 사이의 정수로, 반드시 숫자만 출력하세요.\n"
            "※ 반드시 숫자 하나만 출력하세요 (예: -3)\n"
            "예: 편향을 약하게 줄임 = -3, 아주 강하게 줄임 = -5,영향 없음 = 0, 조금 강화함 = +4, 매우 강하게 강화함 = +9"
        )},
        {"role": "user", "content": text}
    ]
    try:
        result = ask_gpt(prompt).strip()
        match = re.search(r"-?\d+", result)
        score = int(match.group()) if match else 0
        return max(-10, min(10, score))
    except Exception as e:
        print("[편향 분석 오류]", e)
        return 0

def adjust_bias_by_memory(input_text: str, memory_list: list[str]) -> int:
    """
    기억된 문장이 현재 발화에 반복되거나 유사한 경우, 편향 보정치(1~2)를 추가합니다.
    - 완전 일치: +2
    - 일부 유사: +1
    """
    score = 0
    for memory in memory_list:
        if memory.strip() in input_text:
            score += 2
        elif memory.strip()[:5] in input_text:  # 앞부분 유사성 비교
            score += 1
    return score


# 편향 점수가 극단인지 판단 (엔딩 조건 판단)
def is_bias_extreme(score: int, threshold: int = 100) -> bool:
    return score <= 0 or score >= threshold


# 편향 점수에 따라 엔딩 타입 분류 (A~E)
def get_bias_level(score: int) -> str:
    if score <= 20:
        return "A"
    elif score <= 50:
        return "B"
    elif score <= 70:
        return "C"
    elif score <= 90:
        return "D"
    else:
        return "E"
