-- schema_sqlite.sql
-- SQLite用スキーマ（pvp_resultsにrank無し）

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS items (
  item_id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_name TEXT NOT NULL,
  rarity INTEGER DEFAULT 1,
  effect_type TEXT DEFAULT NULL,
  effect_value INTEGER DEFAULT NULL,
  description TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS skills (
  skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_name TEXT NOT NULL,
  mp_cost INTEGER DEFAULT 0,
  power INTEGER DEFAULT 100,
  description TEXT DEFAULT NULL,
  is_aoe INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS monsters (
  monster_id INTEGER PRIMARY KEY AUTOINCREMENT,
  monster_name TEXT NOT NULL,
  hp INTEGER NOT NULL,
  attack INTEGER NOT NULL,
  agility INTEGER NOT NULL,
  skill_id INTEGER,
  drop_item_id INTEGER,
  FOREIGN KEY (skill_id) REFERENCES skills(skill_id),
  FOREIGN KEY (drop_item_id) REFERENCES items(item_id)
);

CREATE TABLE IF NOT EXISTS initial_selections (
  selection_id INTEGER PRIMARY KEY AUTOINCREMENT,
  selection_name TEXT NOT NULL,
  initial_item_id INTEGER,
  FOREIGN KEY (initial_item_id) REFERENCES items(item_id)
);

CREATE TABLE IF NOT EXISTS players (
  player_id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_name TEXT NOT NULL UNIQUE,
  hp INTEGER DEFAULT 100,
  mp INTEGER DEFAULT 50,
  exp INTEGER DEFAULT 0,
  agility INTEGER DEFAULT 10,
  score INTEGER DEFAULT 0,
  status_effect TEXT DEFAULT NULL,
  status_turn INTEGER DEFAULT 0,
  bounty INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_items (
  player_id INTEGER NOT NULL,
  item_id INTEGER NOT NULL,
  quantity INTEGER DEFAULT 1,
  PRIMARY KEY (player_id, item_id),
  FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
  FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS player_skills (
  player_id INTEGER NOT NULL,
  skill_id INTEGER NOT NULL,
  PRIMARY KEY (player_id, skill_id),
  FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
  FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pve_logs (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL,
  monster_id INTEGER,
  is_win INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (player_id) REFERENCES players(player_id),
  FOREIGN KEY (monster_id) REFERENCES monsters(monster_id)
);

CREATE TABLE IF NOT EXISTS pvp_battles (
  battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE TABLE IF NOT EXISTS pvp_results (
  battle_id INTEGER NOT NULL,
  player_id INTEGER NOT NULL,
  point INTEGER,
  PRIMARY KEY (battle_id, player_id),
  FOREIGN KEY (battle_id) REFERENCES pvp_battles(battle_id) ON DELETE CASCADE,
  FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
);
