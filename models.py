from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    npc_id = Column(String(50), nullable=False)     # 예: '영희'
    role = Column(String(10), nullable=False)        # 예: 'user' 또는 'assistant'
    content = Column(Text, nullable=False)           # 메시지 내용
    timestamp = Column(DateTime, default=datetime.utcnow)

class HighlightedMemory(Base):
    __tablename__ = "highlighted_memory"
    id = Column(Integer, primary_key=True, index=True)
    npc_id = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class EmotionState(Base):
    __tablename__ = "emotion_state"

    npc_id = Column(String(50), primary_key=True)
    joy = Column(Integer, default=0)
    sadness = Column(Integer, default=0)
    anger = Column(Integer, default=0)
    anxiety = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class BiasState(Base):
    __tablename__ = "bias_state"

    npc_id = Column(String(50), primary_key=True)
    score = Column(Integer, default=10)
    last_updated = Column(DateTime, default=datetime.utcnow)