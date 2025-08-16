from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    whatsapp_user_id: Mapped[str] = mapped_column(String(64), index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    interactions: Mapped[list[Interaction]] = relationship("Interaction", back_populates="user")
    memories: Mapped[list[Memory]] = relationship("Memory", back_populates="user")


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        UniqueConstraint("twilio_message_sid", name="uq_interactions_twilio_sid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    twilio_message_sid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    message_direction: Mapped[str] = mapped_column(String(16), default="inbound")  # inbound/outbound
    message_type: Mapped[str] = mapped_column(String(16))  # text/image/audio
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="interactions")
    media_assets: Mapped[list[MediaAsset]] = relationship("MediaAsset", back_populates="interaction")
    memory: Mapped[Optional[Memory]] = relationship("Memory", back_populates="interaction", uselist=False)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint("sha256_hash", name="uq_media_assets_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interactions.id", ondelete="CASCADE"))

    media_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(128), index=True)

    width_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    interaction: Mapped[Interaction] = relationship("Interaction", back_populates="media_assets")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interactions.id", ondelete="SET NULL"))

    mem0_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    memory_type: Mapped[str] = mapped_column(String(16))  # text/image/audio
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # transcript or text
    labels_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    user: Mapped[User] = relationship("User", back_populates="memories")
    interaction: Mapped[Interaction] = relationship("Interaction", back_populates="memory") 