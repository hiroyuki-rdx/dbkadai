-- seed.sql
-- 最低限の初期データ（既にデータがある場合はアプリ側で投入をスキップする想定）

-- skills
INSERT INTO skills (skill_name, mp_cost, power, description, is_aoe) VALUES
('全力斬り', 5, 180, '命中率低/威力180%', FALSE),
('ヒール', 10, 0, 'HP回復', FALSE),
('ファイア', 15, 130, '炎ダメージ130%', FALSE),
('ブリザード', 20, 100, '威力100%+氷結30%', FALSE),
('ポイズン', 8, 40, '威力40%+毒100%', FALSE),
('スタン撃ち', 12, 80, '威力80%+気絶50%', FALSE),
('薙ぎ払い', 10, 50, '全体に威力50%', TRUE),
('アースクエイク', 40, 90, '全体に威力90%', TRUE),
('ドレイン', 15, 80, '威力80%+吸収', FALSE),
('メテオ', 30, 220, '超魔法220%', FALSE),
('隠れ身', 20, 0, 'MP20消費/1ターン隠密', FALSE);

-- items
INSERT INTO items (item_name, rarity, effect_type, effect_value, description) VALUES
('銅の剣', 1, 'pvp_atk', 20, '★ PvP攻撃力+20'),
('銀の剣', 2, 'pvp_atk', 50, '★★ PvP攻撃力+50'),
('勇者の剣', 3, 'pvp_atk', 100, '★★★ PvP攻撃力+100'),
('木の盾', 1, 'pvp_def', 10, '★ PvP防御力+10'),
('鉄の盾', 2, 'pvp_def', 20, '★★ PvP防御力+20'),
('イージスの盾', 3, 'pvp_def', 40, '★★★ PvP防御力+40'),
('疾風のブーツ', 2, 'pvp_spd', 50, '★★ PvP素早さ+50'),
('勝者の指輪', 2, 'pvp_score', 2, '★★ 次のPvPスコア2倍'),
('王者の冠', 3, 'pvp_score', 3, '★★★ 次のPvPスコア3倍'),
('皇帝のマント', 4, 'pvp_score', 5, '★★★★ 次のPvPスコア5倍'),
('薬草', 1, 'pve_heal', 50, '★ HP50回復'),
('経験の書', 2, 'pve_exp', 50, '★★ 経験値+50%'),
('ドラゴンスレイヤー', 3, 'pve_dmg', 100, '★★★ モンスターへのダメ+100%'),
('神の加護', 4, 'bless_regen', 10, '★★★★ 自分のターン開始時HP+10（PvE/PvP）');

-- monsters (任意: 現行実装はPython側固定リストだが、設計に合わせて登録しておく)
INSERT INTO monsters (monster_name, hp, attack, agility, skill_id, drop_item_id) VALUES
('スライム', 30, 10, 10, NULL, NULL),
('ゴブリン', 50, 15, 50, NULL, NULL),
('ドラゴン', 150, 30, 100, NULL, NULL),
('魔王の影', 300, 50, 200, NULL, NULL);

-- initial selections (任意)
INSERT INTO initial_selections (selection_name, initial_item_id) VALUES
('経験値+100 (即レベルアップ)', NULL),
('神の加護', NULL);
