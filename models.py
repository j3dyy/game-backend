from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Hero", nullable=False)
    level = Column(Integer, default=1, nullable=False)
    xp = Column(Integer, default=0, nullable=False)
    next_xp = Column(Integer, default=100, nullable=False)
    gold = Column(Integer, default=50, nullable=False)
    free_stat_points = Column(Integer, default=5, nullable=False)
    str = Column(Integer, default=5, nullable=False)
    agi = Column(Integer, default=5, nullable=False)
    vit = Column(Integer, default=5, nullable=False)
    int = Column(Integer, default=5, nullable=False)
    current_hp = Column(Integer, default=50, nullable=False)
    max_hp = Column(Integer, default=50, nullable=False)
    current_floor = Column(Integer, default=1, nullable=False)
    highest_floor = Column(Integer, default=1, nullable=False)

    items = relationship("Item", back_populates="character", cascade="all, delete-orphan")
    active_battle = relationship(
        "ActiveBattle", back_populates="character", uselist=False, cascade="all, delete-orphan"
    )


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slot = Column(String, nullable=False)  # "weapon" | "armor"
    rarity = Column(String, default="Common", nullable=False)  # "Common" | "Rare" | "Epic"
    bonus_str = Column(Integer, default=0, nullable=False)
    bonus_agi = Column(Integer, default=0, nullable=False)
    bonus_vit = Column(Integer, default=0, nullable=False)
    bonus_int = Column(Integer, default=0, nullable=False)
    is_equipped = Column(Boolean, default=False, nullable=False)
    sell_price = Column(Integer, default=10, nullable=False)

    character = relationship("Character", back_populates="items")


class ActiveBattle(Base):
    __tablename__ = "active_battles"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), unique=True, nullable=False, index=True)
    enemy_name = Column(String, nullable=False)
    enemy_level = Column(Integer, nullable=False)
    enemy_hp = Column(Integer, nullable=False)
    enemy_max_hp = Column(Integer, nullable=False)
    enemy_damage = Column(Integer, nullable=False)
    enemy_xp = Column(Integer, nullable=False)
    enemy_gold = Column(Integer, nullable=False)

    character = relationship("Character", back_populates="active_battle")
