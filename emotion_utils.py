from database import get_session
from models import EmotionState
from openai_client import ask_gpt
from sqlalchemy.orm import Session
from datetime import datetime
import re
import random

# 초기 감정 값
DEFAULT_EMOTION = {
    "joy": random.randint(10, 20),
    "sadness": random.randint(10, 20),
    "anger": random.randint(10, 20),
    "anxiety": random.randint(10, 20),
}

# 감정 축 리스트
EMOTION_AXES = ["joy", "sadness", "anger", "anxiety"]

# 감정별 decay 속도 설정
DECAY_RATES = {
    "joy": 10,
    "sadness": 4,
    "anger": 12,
    "anxiety": 6,
}

# 감정 상태 가져오기 (없으면 생성)
def get_emotions(npc_id: str) -> dict:
    session: Session = get_session()
    state = session.query(EmotionState).filter_by(npc_id=npc_id).first()
    if not state:
        state = EmotionState(npc_id=npc_id, **DEFAULT_EMOTION)
        session.add(state)
        session.commit()
    return {
        "joy": state.joy,
        "sadness": state.sadness,
        "anger": state.anger,
        "anxiety": state.anxiety,
    }

# 감정 상태 업데이트
def update_emotions(npc_id: str, delta_dict: dict):
    session: Session = get_session()
    state = session.query(EmotionState).filter_by(npc_id=npc_id).first()
    if not state:
        state = EmotionState(
            npc_id=npc_id,
            joy=random.randint(10, 20),
            sadness=random.randint(10, 20),
            anger=random.randint(10, 20),
            anxiety=random.randint(10, 20)
        )
        session.add(state)
    for key in DEFAULT_EMOTION.keys():
        delta = delta_dict.get(key, 0)
        current = getattr(state, key)
        setattr(state, key, max(0, min(100, current + delta)))
    state.last_updated = datetime.utcnow()
    session.commit()

# 감정 변화량 분석 (GPT 기반)
def analyze_emotions_from_input(user_input: str) -> dict:
    prompt = [
        {"role": "system", "content": (
            "당신은 감정 분석 시스템입니다. 사용자의 발화가 NPC에게 주는 감정적 영향을 평가하세요.\n"
            "각 감정은 joy, sadness, anger, anxiety 입니다.\n"
            "각 감정마다 -10~+10의 정수로 표현하며, 다음 형식으로 출력하세요:\n"
            "joy: +3\nsadness: -2\nanger: 0\nanxiety: +1"
        )},
        {"role": "user", "content": user_input}
    ]
    try:
        result = ask_gpt(prompt).strip()
        matches = re.findall(r"(joy|sadness|anger|anxiety):\s*([-+]?\d+)", result)
        return {key: int(val) for key, val in matches}
    except Exception as e:
        print("[다축 감정 분석 오류]", e)
        return {k: 0 for k in DEFAULT_EMOTION.keys()}

# 감정 스타일 추론 (주 감정 기준)
def get_dominant_emotion(emotions: dict) -> str:
    return max(emotions.items(), key=lambda x: x[1])[0]

# 기억 기반 감정 조정 함수
def adjust_emotion_by_memory(input_text: str, memory_list: list[str]) -> dict:
    """
    기억된 문장이 현재 발화에 반복되거나 유사한 경우, 감정 변화량을 반환합니다.
    - 반복된 말은 짜증(anger)이나 슬픔(sadness)을 유발할 수 있음
    """
    deltas = {axis: 0 for axis in EMOTION_AXES}
    for memory in memory_list:
        if memory.strip() in input_text:
            deltas["anger"] += 2
            deltas["sadness"] += 1
    return deltas

# 감정 폭주 상태 감지 함수
def is_emotion_uncontrolled(emotions: dict, threshold: int = 100) -> bool:
    return any(score >= threshold for score in emotions.values())

# 감정 포화 후 감소 로직 (감정별 속도 적용)
def decay_saturated_emotions(npc_id: str, threshold: int = 100):
    session = get_session()
    state = session.query(EmotionState).filter_by(npc_id=npc_id).first()
    if not state:
        return

    updated = False
    for key in EMOTION_AXES:
        current = getattr(state, key)
        if current >= threshold:
            decay = DECAY_RATES.get(key, 8)
            setattr(state, key, max(0, current - decay))
            updated = True

    if updated:
        state.last_updated = datetime.utcnow()
        session.commit()

# GPT 기반 감정 회복 분석
def analyze_emotion_recovery(ai_reply: str, current_emotions: dict) -> dict:
    prompt = [
        {"role": "system", "content": (
            "당신은 감정 상태 분석가입니다. 사용자의 감정 상태가 각각 다음과 같을 때, "
            "AI의 말이 이 감정들을 얼마나 진정시키는지 평가하세요.\n"
            "감정은 joy, sadness, anger, anxiety 네 가지입니다.\n"
            "각 감정에 대해 회복 효과가 있다면 0~-10 사이의 정수로 표현하세요.\n"
            "형식은 다음과 같습니다:\n"
            "joy: -3\nsadness: 0\nanger: -8\nanxiety: -5"
        )},
        {"role": "user", "content": f"현재 감정 상태: {current_emotions}"},
        {"role": "assistant", "content": "이제 AI의 말입니다:"},
        {"role": "user", "content": ai_reply}
    ]
    try:
        result = ask_gpt(prompt).strip()
        matches = re.findall(r"(joy|sadness|anger|anxiety):\s*(-?\d+)", result)
        return {key: int(val) for key, val in matches}
    except Exception as e:
        print("[감정 회복 분석 오류]", e)
        return {key: 0 for key in EMOTION_AXES}

# AI 응답 기반 감정 회복 적용
def apply_recovery_if_valid(npc_id: str, ai_reply: str):
    session = get_session()
    state = session.query(EmotionState).filter_by(npc_id=npc_id).first()
    if not state:
        return

    current_emotions = {axis: getattr(state, axis) for axis in EMOTION_AXES}
    recovery = analyze_emotion_recovery(ai_reply, current_emotions)

    updated = False
    for axis in EMOTION_AXES:
        delta = recovery.get(axis, 0)
        if delta < 0:
            new_value = max(0, getattr(state, axis) + delta)
            setattr(state, axis, new_value)
            updated = True

    if updated:
        state.last_updated = datetime.utcnow()
        session.commit()