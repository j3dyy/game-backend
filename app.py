import os
import random
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import engine, get_db, Base
import models

app = FastAPI(title="RPG Game Backend", version="1.0.0")

@app.on_event("startup")
def on_startup():
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✔ PostgreSQL database tables initialized successfully.")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize database tables on startup: {e}")

# CORS middleware for cross-origin frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Pydantic Request Schemas
# -------------------------------------------------------------------
class StatAllocateRequest(BaseModel):
    stat: str  # "str" | "agi" | "vit" | "int"


class DungeonActionRequest(BaseModel):
    action: str  # "attack" | "flee" | "heal"


class ItemActionRequest(BaseModel):
    item_id: int


class UnequipRequest(BaseModel):
    item_id: Optional[int] = None
    slot: Optional[str] = None  # "weapon" | "armor"


# -------------------------------------------------------------------
# Helper & Business Logic Functions
# -------------------------------------------------------------------
def get_or_create_character(db: Session) -> models.Character:
    char = db.query(models.Character).first()
    if not char:
        char = models.Character(
            name="Hero",
            level=1,
            xp=0,
            next_xp=100,
            gold=50,
            free_stat_points=5,
            str=5,
            agi=5,
            vit=5,
            int=5,
            current_hp=50,
            max_hp=50,
            current_floor=1,
            highest_floor=1,
        )
        db.add(char)
        db.commit()
        db.refresh(char)

        # Starter Weapon
        starter_weapon = models.Item(
            character_id=char.id,
            name="Rusty Iron Sword",
            slot="weapon",
            rarity="Common",
            bonus_str=2,
            bonus_agi=0,
            bonus_vit=0,
            bonus_int=0,
            is_equipped=True,
            sell_price=10,
        )
        # Starter Armor
        starter_armor = models.Item(
            character_id=char.id,
            name="Worn Leather Tunic",
            slot="armor",
            rarity="Common",
            bonus_str=0,
            bonus_agi=1,
            bonus_vit=2,
            bonus_int=0,
            is_equipped=True,
            sell_price=10,
        )
        db.add_all([starter_weapon, starter_armor])
        db.commit()
        db.refresh(char)

        # Calculate initial Max HP and set current HP
        stats = calculate_stats(char)
        char.max_hp = stats["max_hp"]
        char.current_hp = char.max_hp
        db.commit()
        db.refresh(char)

    return char


def calculate_stats(char: models.Character) -> Dict[str, Any]:
    bonus_str = sum(item.bonus_str for item in char.items if item.is_equipped)
    bonus_agi = sum(item.bonus_agi for item in char.items if item.is_equipped)
    bonus_vit = sum(item.bonus_vit for item in char.items if item.is_equipped)
    bonus_int = sum(item.bonus_int for item in char.items if item.is_equipped)

    total_str = char.str + bonus_str
    total_agi = char.agi + bonus_agi
    total_vit = char.vit + bonus_vit
    total_int = char.int + bonus_int

    max_hp = total_vit * 10
    attack_power = total_str * 2
    dodge_chance = min(0.50, round(total_agi * 0.005, 4))
    crit_chance = min(0.60, round(total_agi * 0.004, 4))

    return {
        "base_str": char.str,
        "base_agi": char.agi,
        "base_vit": char.vit,
        "base_int": char.int,
        "bonus_str": bonus_str,
        "bonus_agi": bonus_agi,
        "bonus_vit": bonus_vit,
        "bonus_int": bonus_int,
        "total_str": total_str,
        "total_agi": total_agi,
        "total_vit": total_vit,
        "total_int": total_int,
        "max_hp": max_hp,
        "attack_power": attack_power,
        "dodge_chance": dodge_chance,
        "crit_chance": crit_chance,
    }


def serialize_character_state(char: models.Character) -> Dict[str, Any]:
    stats = calculate_stats(char)

    # Sync max_hp if out of sync
    if char.max_hp != stats["max_hp"]:
        char.max_hp = stats["max_hp"]
    if char.current_hp > char.max_hp:
        char.current_hp = char.max_hp

    equipped_weapon = next((item for item in char.items if item.is_equipped and item.slot == "weapon"), None)
    equipped_armor = next((item for item in char.items if item.is_equipped and item.slot == "armor"), None)

    return {
        "character": {
            "id": char.id,
            "name": char.name,
            "level": char.level,
            "xp": char.xp,
            "next_xp": char.next_xp,
            "gold": char.gold,
            "free_stat_points": char.free_stat_points,
            "current_hp": char.current_hp,
            "max_hp": char.max_hp,
            "current_floor": char.current_floor,
            "highest_floor": char.highest_floor,
        },
        "stats": stats,
        "inventory": [
            {
                "id": item.id,
                "name": item.name,
                "slot": item.slot,
                "rarity": item.rarity,
                "bonus_str": item.bonus_str,
                "bonus_agi": item.bonus_agi,
                "bonus_vit": item.bonus_vit,
                "bonus_int": item.bonus_int,
                "is_equipped": item.is_equipped,
                "sell_price": item.sell_price,
            }
            for item in sorted(char.items, key=lambda x: (not x.is_equipped, x.id))
        ],
        "equipment": {
            "weapon": {
                "id": equipped_weapon.id,
                "name": equipped_weapon.name,
                "rarity": equipped_weapon.rarity,
                "bonus_str": equipped_weapon.bonus_str,
                "bonus_agi": equipped_weapon.bonus_agi,
                "bonus_vit": equipped_weapon.bonus_vit,
                "bonus_int": equipped_weapon.bonus_int,
                "sell_price": equipped_weapon.sell_price,
            } if equipped_weapon else None,
            "armor": {
                "id": equipped_armor.id,
                "name": equipped_armor.name,
                "rarity": equipped_armor.rarity,
                "bonus_str": equipped_armor.bonus_str,
                "bonus_agi": equipped_armor.bonus_agi,
                "bonus_vit": equipped_armor.bonus_vit,
                "bonus_int": equipped_armor.bonus_int,
                "sell_price": equipped_armor.sell_price,
            } if equipped_armor else None,
        },
        "active_battle": {
            "id": char.active_battle.id,
            "enemy_name": char.active_battle.enemy_name,
            "enemy_level": char.active_battle.enemy_level,
            "enemy_hp": char.active_battle.enemy_hp,
            "enemy_max_hp": char.active_battle.enemy_max_hp,
            "enemy_damage": char.active_battle.enemy_damage,
            "enemy_xp": char.active_battle.enemy_xp,
            "enemy_gold": char.active_battle.enemy_gold,
        } if char.active_battle else None,
    }


def generate_enemy_for_floor(floor: int) -> Dict[str, Any]:
    if floor <= 3:
        enemy_names = ["Slime Fiend", "Goblin Scout", "Cave Bat", "Wild Dire Wolf"]
    elif floor <= 7:
        enemy_names = ["Skeleton Warrior", "Zombie Brute", "Hobgoblin Raider", "Cavern Spider Queen"]
    elif floor <= 12:
        enemy_names = ["Orc Berserker", "Shadow Wraith", "Gargoyle Sentry", "Necromancer Cultist"]
    elif floor <= 18:
        enemy_names = ["Dark Knight", "Raging Minotaur", "Infernal Elemental", "Vampire Lord"]
    else:
        enemy_names = ["Abyssal Drake", "Elder Lich", "Titan Golem", "Archdemon of Ruin"]

    name = random.choice(enemy_names)
    level = floor
    max_hp = 35 + (floor - 1) * 20 + random.randint(-4, 6)
    damage = max(4, int(6 + (floor - 1) * 3.5 + random.randint(-1, 3)))
    xp = 25 + floor * 15 + random.randint(0, 8)
    gold = 12 + floor * 8 + random.randint(1, 8)

    return {
        "enemy_name": f"{name} (Lv.{level})",
        "enemy_level": level,
        "enemy_hp": max_hp,
        "enemy_max_hp": max_hp,
        "enemy_damage": damage,
        "enemy_xp": xp,
        "enemy_gold": gold,
    }


def generate_random_loot(floor: int, character_id: int) -> models.Item:
    slot = random.choice(["weapon", "armor"])
    rarity_roll = random.random()

    if rarity_roll < 0.65:
        rarity = "Common"
        stat_points = random.randint(1, max(2, floor))
        sell_price = 10 + floor * 3
    elif rarity_roll < 0.90:
        rarity = "Rare"
        stat_points = random.randint(3, max(4, floor * 2))
        sell_price = 25 + floor * 7
    else:
        rarity = "Epic"
        stat_points = random.randint(6, max(8, floor * 3))
        sell_price = 60 + floor * 15

    # Random prefixes & base names
    common_weapons = ["Shortsword", "Dagger", "Mace", "Hunting Bow", "Handaxe"]
    rare_weapons = ["Runed Broadsword", "Shadowblade", "Frost Flail", "War Cleaver"]
    epic_weapons = ["Doomcaller", "Sunfire Greatsword", "Soulstealer", "Thunderfury"]

    common_armors = ["Cloth Robe", "Leather Vest", "Hide Cuirass", "Padded Jerkin"]
    rare_armors = ["Reinforced Chainmail", "Iron Hauberk", "Shadow Cloak", "Knight Plate"]
    epic_armors = ["Dragonscale Armor", "Aegis of the Sun", "Abyssal Carapace", "Celestial Regalia"]

    if slot == "weapon":
        if rarity == "Common":
            name = random.choice(common_weapons)
        elif rarity == "Rare":
            name = random.choice(rare_weapons)
        else:
            name = random.choice(epic_weapons)
    else:
        if rarity == "Common":
            name = random.choice(common_armors)
        elif rarity == "Rare":
            name = random.choice(rare_armors)
        else:
            name = random.choice(epic_armors)

    bonus_str = 0
    bonus_agi = 0
    bonus_vit = 0
    bonus_int = 0

    # Distribute stat points
    for _ in range(stat_points):
        chosen_stat = random.choice(["str", "agi", "vit", "int"])
        if chosen_stat == "str":
            bonus_str += 1
        elif chosen_stat == "agi":
            bonus_agi += 1
        elif chosen_stat == "vit":
            bonus_vit += 1
        else:
            bonus_int += 1

    return models.Item(
        character_id=character_id,
        name=name,
        slot=slot,
        rarity=rarity,
        bonus_str=bonus_str,
        bonus_agi=bonus_agi,
        bonus_vit=bonus_vit,
        bonus_int=bonus_int,
        is_equipped=False,
        sell_price=sell_price,
    )


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    """Simple status check for PaaS health monitors."""
    return {"status": "ok"}


@app.get("/api/state")
def get_game_state(db: Session = Depends(get_db)):
    """Returns character sheet, inventory, equipment, and active battle."""
    char = get_or_create_character(db)
    return serialize_character_state(char)


@app.post("/api/character/allocate")
def allocate_stat(req: StatAllocateRequest, db: Session = Depends(get_db)):
    """Allocate an unspent stat point to STR, AGI, VIT, or INT."""
    char = get_or_create_character(db)
    if char.free_stat_points <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No free stat points available.",
        )

    stat_lower = req.stat.lower().strip()
    if stat_lower == "str":
        char.str += 1
    elif stat_lower == "agi":
        char.agi += 1
    elif stat_lower == "vit":
        char.vit += 1
    elif stat_lower == "int":
        char.int += 1
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stat name. Choose from 'str', 'agi', 'vit', 'int'.",
        )

    char.free_stat_points -= 1
    stats = calculate_stats(char)
    char.max_hp = stats["max_hp"]

    # When VIT is upgraded, heal the player by the newly gained 10 HP
    if stat_lower == "vit":
        char.current_hp = min(char.max_hp, char.current_hp + 10)

    db.commit()
    db.refresh(char)

    return {
        "message": f"Allocated 1 point to {stat_lower.upper()}!",
        "state": serialize_character_state(char),
    }


@app.post("/api/dungeon/enter")
def enter_dungeon(db: Session = Depends(get_db)):
    """Spawns an enemy scaled to the current floor or returns active battle."""
    char = get_or_create_character(db)

    if char.active_battle:
        return {
            "message": f"Already facing {char.active_battle.enemy_name}!",
            "battle": {
                "id": char.active_battle.id,
                "enemy_name": char.active_battle.enemy_name,
                "enemy_level": char.active_battle.enemy_level,
                "enemy_hp": char.active_battle.enemy_hp,
                "enemy_max_hp": char.active_battle.enemy_max_hp,
                "enemy_damage": char.active_battle.enemy_damage,
                "enemy_xp": char.active_battle.enemy_xp,
                "enemy_gold": char.active_battle.enemy_gold,
            },
            "state": serialize_character_state(char),
        }

    enemy_data = generate_enemy_for_floor(char.current_floor)
    battle = models.ActiveBattle(
        character_id=char.id,
        enemy_name=enemy_data["enemy_name"],
        enemy_level=enemy_data["enemy_level"],
        enemy_hp=enemy_data["enemy_hp"],
        enemy_max_hp=enemy_data["enemy_max_hp"],
        enemy_damage=enemy_data["enemy_damage"],
        enemy_xp=enemy_data["enemy_xp"],
        enemy_gold=enemy_data["enemy_gold"],
    )
    db.add(battle)
    db.commit()
    db.refresh(char)

    return {
        "message": f"Entered Floor {char.current_floor}! A wild {battle.enemy_name} appears!",
        "battle": {
            "id": battle.id,
            "enemy_name": battle.enemy_name,
            "enemy_level": battle.enemy_level,
            "enemy_hp": battle.enemy_hp,
            "enemy_max_hp": battle.enemy_max_hp,
            "enemy_damage": battle.enemy_damage,
            "enemy_xp": battle.enemy_xp,
            "enemy_gold": battle.enemy_gold,
        },
        "state": serialize_character_state(char),
    }


@app.post("/api/dungeon/action")
def dungeon_action(req: DungeonActionRequest, db: Session = Depends(get_db)):
    """Execute combat action: attack, heal, or flee."""
    char = get_or_create_character(db)
    battle = char.active_battle
    if not battle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active battle. Enter the dungeon first!",
        )

    stats = calculate_stats(char)
    action = req.action.lower().strip()
    logs: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------
    # ACTION: ATTACK
    # ---------------------------------------------------------------
    if action == "attack":
        # Player rolls crit
        is_crit = random.random() < stats["crit_chance"]
        damage = int(stats["attack_power"] * 1.5) if is_crit else stats["attack_power"]
        battle.enemy_hp = max(0, battle.enemy_hp - damage)

        if is_crit:
            logs.append({
                "type": "crit",
                "text": f"💥 CRITICAL HIT! You strike {battle.enemy_name} for {damage} damage! ({battle.enemy_hp}/{battle.enemy_max_hp} HP)",
            })
        else:
            logs.append({
                "type": "player_attack",
                "text": f"⚔️ You attack {battle.enemy_name} for {damage} damage! ({battle.enemy_hp}/{battle.enemy_max_hp} HP)",
            })

        # Check if enemy is slain
        if battle.enemy_hp <= 0:
            earned_xp = battle.enemy_xp
            earned_gold = battle.enemy_gold
            char.xp += earned_xp
            char.gold += earned_gold

            logs.append({
                "type": "victory",
                "text": f"🏆 {battle.enemy_name} has been defeated! Earned +{earned_xp} XP and +{earned_gold} Gold.",
            })

            # Roll 35% chance for loot drop
            loot_item = None
            if random.random() < 0.35:
                loot_item = generate_random_loot(char.current_floor, char.id)
                db.add(loot_item)
                db.flush()
                stat_desc = []
                if loot_item.bonus_str: stat_desc.append(f"+{loot_item.bonus_str} STR")
                if loot_item.bonus_agi: stat_desc.append(f"+{loot_item.bonus_agi} AGI")
                if loot_item.bonus_vit: stat_desc.append(f"+{loot_item.bonus_vit} VIT")
                if loot_item.bonus_int: stat_desc.append(f"+{loot_item.bonus_int} INT")
                stat_str = ", ".join(stat_desc) if stat_desc else "Standard quality"
                logs.append({
                    "type": "loot",
                    "text": f"🎁 Loot dropped: [{loot_item.rarity}] {loot_item.name} ({stat_str})!",
                })

            # Level-up Check
            leveled_up = False
            while char.xp >= char.next_xp:
                char.level += 1
                char.xp -= char.next_xp
                char.next_xp = int(char.next_xp * 1.5)
                char.free_stat_points += 3
                char.current_hp = stats["max_hp"]
                leveled_up = True
                logs.append({
                    "type": "level_up",
                    "text": f"🌟 LEVEL UP! You reached Level {char.level}! (+3 Free Stat Points, HP fully restored)",
                })

            # Advance Dungeon Floor
            prev_floor = char.current_floor
            char.current_floor += 1
            if char.current_floor > char.highest_floor:
                char.highest_floor = char.current_floor
            logs.append({
                "type": "floor_advance",
                "text": f"🚪 Floor {prev_floor} cleared! The path to Floor {char.current_floor} is now open.",
            })

            # Clean up active battle
            db.delete(battle)
            db.commit()
            db.refresh(char)

            return {
                "result": "victory",
                "logs": logs,
                "state": serialize_character_state(char),
            }

        # Enemy survived -> Enemy attacks!
        is_dodged = random.random() < stats["dodge_chance"]
        if is_dodged:
            logs.append({
                "type": "dodge",
                "text": f"💨 DODGED! {battle.enemy_name} attacks for {battle.enemy_damage} damage, but you agilely evade!",
            })
        else:
            char.current_hp = max(0, char.current_hp - battle.enemy_damage)
            logs.append({
                "type": "enemy_attack",
                "text": f"🩸 {battle.enemy_name} hits you for {battle.enemy_damage} damage! ({char.current_hp}/{stats['max_hp']} HP)",
            })

        # Check player death
        if char.current_hp <= 0:
            lost_gold = int(char.gold * 0.20)
            char.gold = max(0, char.gold - lost_gold)
            char.current_floor = 1
            char.current_hp = stats["max_hp"]

            logs.append({
                "type": "death",
                "text": f"💀 YOU DIED! You collapsed on Floor {char.current_floor}. Returned to Floor 1, HP restored, lost {lost_gold} Gold.",
            })

            db.delete(battle)
            db.commit()
            db.refresh(char)

            return {
                "result": "defeat",
                "logs": logs,
                "state": serialize_character_state(char),
            }

        db.commit()
        db.refresh(char)
        return {
            "result": "turn_ongoing",
            "logs": logs,
            "state": serialize_character_state(char),
        }

    # ---------------------------------------------------------------
    # ACTION: HEAL (Magic Spell)
    # ---------------------------------------------------------------
    elif action == "heal":
        heal_amount = max(20, stats["total_int"] * 3)
        old_hp = char.current_hp
        char.current_hp = min(stats["max_hp"], char.current_hp + heal_amount)
        actual_heal = char.current_hp - old_hp

        logs.append({
            "type": "heal",
            "text": f"✨ You channel spiritual energy and restore {actual_heal} HP! ({char.current_hp}/{stats['max_hp']} HP)",
        })

        # Enemy counter-attacks during heal cast
        is_dodged = random.random() < stats["dodge_chance"]
        if is_dodged:
            logs.append({
                "type": "dodge",
                "text": f"💨 While casting, you deftly dodge {battle.enemy_name}'s counter-strike!",
            })
        else:
            char.current_hp = max(0, char.current_hp - battle.enemy_damage)
            logs.append({
                "type": "enemy_attack",
                "text": f"🩸 {battle.enemy_name} strikes you while casting for {battle.enemy_damage} damage! ({char.current_hp}/{stats['max_hp']} HP)",
            })

        if char.current_hp <= 0:
            lost_gold = int(char.gold * 0.20)
            char.gold = max(0, char.gold - lost_gold)
            char.current_floor = 1
            char.current_hp = stats["max_hp"]

            logs.append({
                "type": "death",
                "text": f"💀 YOU DIED! Fallen during casting. Returned to Floor 1, lost {lost_gold} Gold.",
            })
            db.delete(battle)
            db.commit()
            db.refresh(char)
            return {
                "result": "defeat",
                "logs": logs,
                "state": serialize_character_state(char),
            }

        db.commit()
        db.refresh(char)
        return {
            "result": "turn_ongoing",
            "logs": logs,
            "state": serialize_character_state(char),
        }

    # ---------------------------------------------------------------
    # ACTION: FLEE
    # ---------------------------------------------------------------
    elif action == "flee":
        # 60% base flee chance + minor bonus from AGI
        flee_chance = min(0.85, 0.60 + (stats["total_agi"] * 0.005))
        if random.random() < flee_chance:
            logs.append({
                "type": "flee_success",
                "text": f"🏃💨 You successfully fled from {battle.enemy_name} and retreated to safety!",
            })
            db.delete(battle)
            db.commit()
            db.refresh(char)
            return {
                "result": "fled",
                "logs": logs,
                "state": serialize_character_state(char),
            }
        else:
            logs.append({
                "type": "flee_failed",
                "text": f"🚫 Escape blocked! {battle.enemy_name} cuts off your retreat!",
            })
            char.current_hp = max(0, char.current_hp - battle.enemy_damage)
            logs.append({
                "type": "enemy_attack",
                "text": f"🩸 {battle.enemy_name} strikes your exposed back for {battle.enemy_damage} damage! ({char.current_hp}/{stats['max_hp']} HP)",
            })

            if char.current_hp <= 0:
                lost_gold = int(char.gold * 0.20)
                char.gold = max(0, char.gold - lost_gold)
                char.current_floor = 1
                char.current_hp = stats["max_hp"]

                logs.append({
                    "type": "death",
                    "text": f"💀 YOU DIED while attempting to flee. Returned to Floor 1, lost {lost_gold} Gold.",
                })
                db.delete(battle)
                db.commit()
                db.refresh(char)
                return {
                    "result": "defeat",
                    "logs": logs,
                    "state": serialize_character_state(char),
                }

            db.commit()
            db.refresh(char)
            return {
                "result": "turn_ongoing",
                "logs": logs,
                "state": serialize_character_state(char),
            }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action '{action}'. Valid actions are 'attack', 'heal', 'flee'.",
        )


@app.post("/api/inventory/equip")
def equip_item(req: ItemActionRequest, db: Session = Depends(get_db)):
    """Equips an item, unequipping any currently equipped item in the same slot."""
    char = get_or_create_character(db)
    target_item = db.query(models.Item).filter(
        models.Item.id == req.item_id,
        models.Item.character_id == char.id,
    ).first()

    if not target_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in inventory.",
        )

    # Unequip any item currently equipped in this slot
    for item in char.items:
        if item.slot == target_item.slot and item.is_equipped:
            item.is_equipped = False

    target_item.is_equipped = True

    # Recalculate stats and adjust max/current hp
    stats = calculate_stats(char)
    char.max_hp = stats["max_hp"]
    if char.current_hp > char.max_hp:
        char.current_hp = char.max_hp

    db.commit()
    db.refresh(char)

    return {
        "message": f"Equipped {target_item.name}!",
        "state": serialize_character_state(char),
    }


@app.post("/api/inventory/unequip")
def unequip_item(req: UnequipRequest, db: Session = Depends(get_db)):
    """Unequips an equipped item by ID or slot."""
    char = get_or_create_character(db)

    item_to_unequip = None
    if req.item_id is not None:
        item_to_unequip = db.query(models.Item).filter(
            models.Item.id == req.item_id,
            models.Item.character_id == char.id,
            models.Item.is_equipped == True,
        ).first()
    elif req.slot:
        item_to_unequip = db.query(models.Item).filter(
            models.Item.slot == req.slot.lower().strip(),
            models.Item.character_id == char.id,
            models.Item.is_equipped == True,
        ).first()

    if not item_to_unequip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching equipped item found to unequip.",
        )

    item_to_unequip.is_equipped = False

    stats = calculate_stats(char)
    char.max_hp = stats["max_hp"]
    if char.current_hp > char.max_hp:
        char.current_hp = char.max_hp

    db.commit()
    db.refresh(char)

    return {
        "message": f"Unequipped {item_to_unequip.name}!",
        "state": serialize_character_state(char),
    }


@app.post("/api/inventory/sell")
def sell_item(req: ItemActionRequest, db: Session = Depends(get_db)):
    """Sells an inventory item for gold."""
    char = get_or_create_character(db)
    target_item = db.query(models.Item).filter(
        models.Item.id == req.item_id,
        models.Item.character_id == char.id,
    ).first()

    if not target_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in inventory.",
        )

    if target_item.is_equipped:
        target_item.is_equipped = False

    gold_earned = target_item.sell_price
    char.gold += gold_earned
    item_name = target_item.name

    db.delete(target_item)

    stats = calculate_stats(char)
    char.max_hp = stats["max_hp"]
    if char.current_hp > char.max_hp:
        char.current_hp = char.max_hp

    db.commit()
    db.refresh(char)

    return {
        "message": f"Sold {item_name} for {gold_earned} Gold!",
        "state": serialize_character_state(char),
    }


@app.post("/api/shop/buy-potion")
def buy_potion(db: Session = Depends(get_db)):
    """Costs 15 gold, restores 30 HP (capped at max HP)."""
    char = get_or_create_character(db)
    POTION_COST = 15
    HEAL_AMOUNT = 30

    if char.gold < POTION_COST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough gold! Health Potion costs {POTION_COST} Gold, you have {char.gold}.",
        )

    stats = calculate_stats(char)
    if char.current_hp >= stats["max_hp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your HP is already at maximum!",
        )

    char.gold -= POTION_COST
    old_hp = char.current_hp
    char.current_hp = min(stats["max_hp"], char.current_hp + HEAL_AMOUNT)
    healed = char.current_hp - old_hp

    db.commit()
    db.refresh(char)

    return {
        "message": f"Drank Health Potion! Restored {healed} HP for {POTION_COST} Gold.",
        "state": serialize_character_state(char),
    }


@app.post("/api/shop/rest-inn")
def rest_at_inn(db: Session = Depends(get_db)):
    """Costs 25 gold, restores full HP."""
    char = get_or_create_character(db)
    INN_COST = 25

    if char.gold < INN_COST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough gold! A warm room at the inn costs {INN_COST} Gold.",
        )

    stats = calculate_stats(char)
    if char.current_hp >= stats["max_hp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already fully rested!",
        )

    char.gold -= INN_COST
    char.current_hp = stats["max_hp"]

    db.commit()
    db.refresh(char)

    return {
        "message": f"Rested peacefully at the inn. Health fully restored for {INN_COST} Gold.",
        "state": serialize_character_state(char),
    }


# -------------------------------------------------------------------
# Direct Execution Runner (PaaS / CLI compatible)
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting RPG Game Backend on 0.0.0.0:{port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
