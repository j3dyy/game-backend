# ⚔️ Dungeon Chronicles: Realm of Shadows

A complete, decoupled, server-authoritative web-based RPG built with **Python 3 (FastAPI + SQLAlchemy + SQLite)** and **Vanilla ES6 Web Frontend (HTML5 + Dark Fantasy CSS + Web Audio)**.

Engineered specifically for local development and zero-Docker PaaS cloud deployment via the **`usectl` CLI**.

---

## 📂 Project Architecture & Directory Layout

The project is decoupled into two independent subdirectories:

```
rpg-game/
├── backend/
│   ├── app.py              # FastAPI server, REST API, authoritative combat engine
│   ├── models.py           # SQLAlchemy database schemas (Character, Item, ActiveBattle)
│   ├── database.py         # SQLite engine, session generator, startup init
│   ├── requirements.txt    # Python dependencies (fastapi, uvicorn, sqlalchemy, pydantic)
│   ├── Procfile            # PaaS command: web: uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
│   ├── run.sh              # Local CLI runner with virtual environment setup
│   └── verify_backend.py   # Automated test suite for game mechanics and API endpoints
├── frontend/
│   ├── index.html          # Responsive 3-column UI (Stats, Dungeon Arena, Backpack & Shop)
│   ├── style.css           # Dark-fantasy aesthetic, responsive grid, animated vbars & rarity glows
│   ├── app.js              # Vanilla ES6 state manager, API client, combat logger, Web Audio synth
│   ├── config.js           # Dynamic runtime API base configuration
│   ├── Procfile            # PaaS command: web: python3 -m http.server ${PORT:-3000} --bind 0.0.0.0
│   └── run.sh              # Local CLI static runner
└── README.md               # End-to-end documentation & operational guide
```

---

## 🚀 Local Development & Testing

### 1. Starting the Backend Locally

The backend binds to `0.0.0.0` and prioritizes the `$PORT` environment variable (falling back to port `8000`).

```bash
cd backend

# Option A: Using the automated runner (handles .venv and dependencies)
./run.sh

# Option B: Manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Check backend health:
```bash
curl http://127.0.0.1:8000/healthz
# Response: {"status": "ok"}
```

View current character sheet and state:
```bash
curl http://127.0.0.1:8000/api/state
```

Run the backend verification suite:
```bash
cd backend
.venv/bin/python3 verify_backend.py
```

### 2. Serving the Frontend Locally

The frontend is pure static web assets with zero build steps or bundlers required.

```bash
cd frontend

# Option A: Using the automated runner
./run.sh

# Option B: Using Python's built-in HTTP server
python3 -m http.server 3000 --bind 0.0.0.0
```

Open your browser at **[http://localhost:3000](http://localhost:3000)**. The frontend automatically detects `localhost` and routes API requests to `http://127.0.0.1:8000/api`.

---

## ☁️ Live Cloud Deployment on usectl

The game is live and accessible online:

- 🎮 **Frontend Web Application**: [https://dungeon-rpg.usectl.com](https://dungeon-rpg.usectl.com)
- ⚙️ **Backend API Service**: [https://rpg-api.usectl.com](https://rpg-api.usectl.com)
- 🩺 **Backend Health Endpoint**: [https://rpg-api.usectl.com/healthz](https://rpg-api.usectl.com/healthz)

### How It Was Provisioned & Deployed with usectl

1. **Create the Machine (Resource Wallet & Namespace)**:
   ```bash
   usectl machines create rpg-game --vcpu 1 --ram 2 --storage 5 -y
   usectl machines update rpg-game --github-token "$GITHUB_PAT"
   ```

2. **Deploy the Backend Pod**:
   ```bash
   usectl machines pods create rpg-game backend \
     --repo https://github.com/j3dyy/game-backend \
     --branch main \
     --port 8000 \
     --domain rpg-api \
     -y

   usectl machines deploy rpg-game backend
   ```

3. **Deploy the Frontend Pod**:
   ```bash
   usectl machines pods create rpg-game frontend \
     --repo https://github.com/j3dyy/game-frontend \
     --branch main \
     --port 80 \
     --domain dungeon-rpg \
     -y

   usectl machines deploy rpg-game frontend
   ```

4. **Monitor Pods and Logs**:
   ```bash
   # Check pod health
   usectl machines pods rpg-game

   # View deployment logs
   usectl machines logs rpg-game -f
   ```

---

## 🐙 Git Remote Repositories Setup

The backend and frontend are pre-initialized as independent Git repositories ready to push to GitHub:

### Backend Repository (`git@github.com:j3dyy/game-backend.git`)
```bash
cd backend
git remote add origin git@github.com:j3dyy/game-backend.git  # Pre-configured
git branch -M main
git push -u origin main
```

### Frontend Repository (`git@github.com:j3dyy/game-frontend.git`)
```bash
cd frontend
git remote add origin git@github.com:j3dyy/game-frontend.git  # Pre-configured
git branch -M main
git push -u origin main
```

---

## 🎮 Game Rules & Mathematical Formulas

All combat rolls, damage formulas, stat derivations, item generation, and level progressions are strictly computed and authoritative on the backend.

### Character Stats
- **Total Stat** = $\text{Base Stat} + \sum (\text{Equipped Item Bonuses})$
- **Max HP** = $\text{Total VIT} \times 10$
- **Attack Power** = $\text{Total STR} \times 2$
- **Dodge Chance** = $\min(0.50, \text{Total AGI} \times 0.005)$
- **Critical Strike Chance** = $\min(0.60, \text{Total AGI} \times 0.004)$
- **Critical Damage** = $\text{Attack Power} \times 1.5$

### Combat Turns (`POST /api/dungeon/action`)
1. **Attack**:
   - Player attacks enemy. If crit roll succeeds, deal 1.5x damage.
   - If enemy HP $\le 0$:
     - Grant XP and Gold.
     - 35% chance to drop random loot (Common / Rare / Epic weapon or armor scaled to floor).
     - Check level-up condition.
     - Advance dungeon floor (`current_floor += 1`).
     - Remove active battle.
   - If enemy survives:
     - Enemy counter-attacks.
     - Player dodge check against Dodge Chance.
     - If hit, deduct enemy damage from player HP.
     - If player HP $\le 0$: Player dies, loses 20% Gold, resets to Floor 1, HP restored to Max, battle cleared.
2. **Heal**:
   - Player casts restorative magic healing $\max(20, \text{Total INT} \times 3)$ HP.
   - Takes a turn: enemy counter-attacks (with dodge check).
3. **Flee**:
   - Player attempts to retreat (60% base chance + AGI modifier).
   - If successful: returns safely to dungeon entrance.
   - If failed: enemy attacks player's exposed back.

### Level-Up Progression
When $\text{XP} \ge \text{Next XP}$:
- $\text{Level} \leftarrow \text{Level} + 1$
- $\text{XP} \leftarrow \text{XP} - \text{Next XP}$
- $\text{Next XP} \leftarrow \lfloor \text{Next XP} \times 1.5 \rfloor$
- $\text{Free Stat Points} \leftarrow \text{Free Stat Points} + 3$
- $\text{Current HP} \leftarrow \text{Max HP}$

---

## 📡 REST API Reference

| Method | Path | Description | Payload / Notes |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` | Health check for PaaS load balancers | Response: `{"status": "ok"}` |
| `GET` | `/api/state` | Returns character sheet, inventory, equipment, active battle | Auto-initializes Hero if database is empty |
| `POST` | `/api/character/allocate` | Spend 1 free stat point | `{"stat": "str" \| "agi" \| "vit" \| "int"}` |
| `POST` | `/api/dungeon/enter` | Spawns a monster scaled to current floor | Starts or resumes active battle |
| `POST` | `/api/dungeon/action` | Execute combat action | `{"action": "attack" \| "heal" \| "flee"}` |
| `POST` | `/api/inventory/equip` | Equip an item from backpack | `{"item_id": 12}` |
| `POST` | `/api/inventory/unequip` | Unequip active item | `{"slot": "weapon" \| "armor"}` or `{"item_id": 12}` |
| `POST` | `/api/inventory/sell` | Sell item for gold | `{"item_id": 12}` |
| `POST` | `/api/shop/buy-potion` | Drink health potion (+30 HP) | Costs 15 Gold |
| `POST` | `/api/shop/rest-inn` | Fully restore HP | Costs 25 Gold |

---

## 🛡️ CORS & Security
- CORS Middleware is configured with `allow_origins=["*"]`, `allow_methods=["*"]`, and `allow_headers=["*"]`.
- Static frontend assets communicate seamlessly across arbitrary origins without cross-origin blocks.
