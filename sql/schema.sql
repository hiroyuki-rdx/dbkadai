-- schema.sql
-- 最終DDL（pvp_resultsにrank無し） + 現行Python実装が必要とする拡張カラムを含む

-- 1. マスタ系
CREATE TABLE IF NOT EXISTS items (
    item_id SERIAL PRIMARY KEY,
    item_name VARCHAR(50) NOT NULL,
    rarity INT DEFAULT 1,
    effect_type VARCHAR(20) DEFAULT NULL,
    effect_value INT DEFAULT NULL,
    description VARCHAR(100) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id SERIAL PRIMARY KEY,
    skill_name VARCHAR(50) NOT NULL,
    mp_cost INT DEFAULT 0,
    power INT DEFAULT 100,
    description VARCHAR(100) DEFAULT NULL,
    is_aoe BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS monsters (
    monster_id SERIAL PRIMARY KEY,
    monster_name VARCHAR(50) NOT NULL,
    hp INT NOT NULL,
    attack INT NOT NULL,
    agility INT NOT NULL,
    skill_id INT,
    drop_item_id INT,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id),
    FOREIGN KEY (drop_item_id) REFERENCES items(item_id)
);

CREATE TABLE IF NOT EXISTS initial_selections (
    selection_id SERIAL PRIMARY KEY,
    selection_name VARCHAR(50) NOT NULL,
    initial_item_id INT,
    FOREIGN KEY (initial_item_id) REFERENCES items(item_id)
);

-- 2. プレイヤー・状態系
CREATE TABLE IF NOT EXISTS players (
    player_id SERIAL PRIMARY KEY,
    player_name VARCHAR(50) NOT NULL UNIQUE,
    hp INT DEFAULT 100,
    mp INT DEFAULT 50,
    exp INT DEFAULT 0,
    agility INT DEFAULT 10,

    -- 現行実装用の拡張カラム
    score INT DEFAULT 0,
    status_effect VARCHAR(20) DEFAULT NULL,
    status_turn INT DEFAULT 0,
    bounty INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_items (
    player_id INT,
    item_id INT,
    quantity INT DEFAULT 1,
    PRIMARY KEY (player_id, item_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS player_skills (
    player_id INT,
    skill_id INT,
    PRIMARY KEY (player_id, skill_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- 3. 履歴・ログ系
CREATE TABLE IF NOT EXISTS pve_logs (
    log_id SERIAL PRIMARY KEY,
    player_id INT NOT NULL,
    monster_id INT,
    is_win BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (monster_id) REFERENCES monsters(monster_id)
);

CREATE TABLE IF NOT EXISTS pvp_battles (
    battle_id SERIAL PRIMARY KEY,
    player_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

-- rankカラムは作らない
CREATE TABLE IF NOT EXISTS pvp_results (
    battle_id INT,
    player_id INT,
    point INT,
    PRIMARY KEY (battle_id, player_id),
    FOREIGN KEY (battle_id) REFERENCES pvp_battles(battle_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
);
