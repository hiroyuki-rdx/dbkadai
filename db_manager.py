# db_manager.py
from __future__ import annotations

from pathlib import Path
import sqlite3
from contextlib import contextmanager

import psycopg2
from psycopg2 import OperationalError

from config import DB_CONFIG

class DBManager:
    def __init__(self):
        self.conn = None
        self.backend = None  # 'postgres' | 'sqlite'
        self._init_db()

    def get_connection(self):
        if self.conn is None or getattr(self.conn, "closed", False):
            # まずPostgreSQLを試し、ダメならSQLiteで“このエディタだけで”動かす
            try:
                self.conn = psycopg2.connect(**DB_CONFIG)
                self.backend = "postgres"
            except OperationalError:
                base_dir = Path(__file__).resolve().parent
                db_path = base_dir / "game.sqlite3"
                self.conn = sqlite3.connect(db_path)
                self.backend = "sqlite"
                try:
                    self.conn.execute("PRAGMA foreign_keys = ON")
                except Exception:
                    pass
        return self.conn

    def _init_db(self):
        conn = self.get_connection()
        if self.backend == "postgres":
            with conn.cursor() as cur:
                self._apply_schema(cur)
                self._seed_if_needed(cur)
            conn.commit()
        else:
            cur = conn.cursor()
            try:
                self._apply_schema(cur)
                self._seed_if_needed(cur)
            finally:
                cur.close()
            conn.commit()

    def _apply_schema(self, cur):
        base_dir = Path(__file__).resolve().parent
        schema_path = base_dir / "sql" / ("schema.sql" if self.backend == "postgres" else "schema_sqlite.sql")
        if not schema_path.exists():
            raise FileNotFoundError(f"schema.sql が見つかりません: {schema_path}")
        self._execute_sql_file(cur, schema_path)

    def _seed_if_needed(self, cur):
        # 既存データがある場合は破壊しない
        cur.execute("SELECT COUNT(*) FROM skills")
        skills_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM items")
        items_count = cur.fetchone()[0]
        if skills_count > 0 and items_count > 0:
            # 既存DBでも、新規追加アイテム等を“追加入力”して差分を吸収
            self._ensure_required_master_data(cur)
            return

        base_dir = Path(__file__).resolve().parent
        seed_path = base_dir / "sql" / ("seed.sql" if self.backend == "postgres" else "seed_sqlite.sql")
        if not seed_path.exists():
            return
        self._execute_sql_file(cur, seed_path)

    def _ensure_required_master_data(self, cur):
        """後から追加した必須マスタを、既存DBへ安全に追加入力する。"""
        # 神の加護: 自分のターン開始時HP+10（PvE/PvP）
        cur.execute(self._ph("SELECT 1 FROM items WHERE item_name = %s LIMIT 1"), ("神の加護",))
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute(
                self._ph(
                    """
                    INSERT INTO items (item_name, rarity, effect_type, effect_value, description)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                ),
                ("神の加護", 4, "bless_regen", 10, "★★★★ 自分のターン開始時HP+10（PvE/PvP）"),
            )

    def _execute_sql_file(self, cur, path: Path):
        sql_text = path.read_text(encoding="utf-8")
        # psycopg2は複文実行を保証しないため、単純に;で分割して順次実行
        statements = [s.strip() for s in sql_text.split(";")]
        for stmt in statements:
            if not stmt or stmt.startswith("--"):
                continue
            cur.execute(stmt)

    def _ph(self, sql: str) -> str:
        return sql if self.backend == "postgres" else sql.replace("%s", "?")

    @contextmanager
    def _cursor(self):
        conn = self.get_connection()
        if self.backend == "postgres":
            with conn.cursor() as cur:
                yield cur
        else:
            cur = conn.cursor()
            try:
                yield cur
            finally:
                cur.close()

    def reset_game_data(self):
        """ゲームを中止した時の初期化（プレイヤー/ログ/対戦結果を全消去）。"""
        conn = self.get_connection()
    def reset_all_game_data(self):
        """ゲームデータを完全に初期化する（プレイヤー、アイテム、ログなど全削除）。"""
        conn = self.get_connection()
        if self.backend == "postgres":
            with self._cursor() as cur:
                cur.execute(
                    "TRUNCATE TABLE pvp_results, pvp_battles, pve_logs, player_items, player_skills, players RESTART IDENTITY CASCADE"
                )
            conn.commit()
            return

        # sqlite
        with self._cursor() as cur:
            for table in [
                "pvp_results",
                "pvp_battles",
                "pve_logs",
                "player_items",
                "player_skills",
                "players",
            ]:
                cur.execute(f"DELETE FROM {table}")
            # SQLiteのAUTOINCREMENTをリセット
            cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('players', 'pvp_battles', 'pve_logs')")
        conn.commit()

    def reset_points(self):
        """ゲーム開始前のポイント初期化（全プレイヤーのscore/bountyを0へ）。"""
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(self._ph("UPDATE players SET score = 0, bounty = 0"))
            # 過去の対戦履歴も削除
            cur.execute("DELETE FROM pvp_battles")
        conn.commit()

    def ensure_cpu_players(self, cpu_names=None):
        """CPUプレイヤーを必ず用意する（存在しなければ作成）。"""
        if cpu_names is None:
            cpu_names = ["CPU_A", "CPU_B", "CPU_C"]

        created_or_found = []
        for name in cpu_names:
            created_or_found.append(self.get_or_create_player(name))

        # 念のため存在確認（握りつぶさず、異常なら落とす）
        with self._cursor() as cur:
            placeholders = ",".join(["%s"] * len(cpu_names))
            sql = f"SELECT player_name FROM players WHERE player_name IN ({placeholders})"
            cur.execute(self._ph(sql), tuple(cpu_names))
            rows = cur.fetchall() or []
        existing = {r[0] for r in rows}
        missing = [n for n in cpu_names if n not in existing]
        if missing:
            raise RuntimeError(f"CPUプレイヤーの作成/確認に失敗しました: {missing}")

        return created_or_found

    def _check_add_column(self, cur, table, col, def_str):
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col}'")
        if not cur.fetchone():
            print(f"⚠️ DBアップデート: {col} を追加")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {def_str}")

    def get_or_create_player(self, name):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph(
                    "SELECT player_id, player_name, hp, mp, exp, agility, score, status_effect, status_turn, bounty FROM players WHERE player_name = %s"
                ),
                (name,),
            )
            player = cur.fetchone()
            if player:
                return player

            if self.backend == "postgres":
                cur.execute(
                    """
                    INSERT INTO players (player_name, hp, mp, exp, agility, score, status_effect, status_turn, bounty)
                    VALUES (%s, 100, 50, 0, 10, 0, NULL, 0, 0)
                    RETURNING player_id, player_name, hp, mp, exp, agility, score, status_effect, status_turn, bounty
                    """,
                    (name,),
                )
                new_player = cur.fetchone()
            else:
                cur.execute(
                    self._ph(
                        """
                        INSERT INTO players (player_name, hp, mp, exp, agility, score, status_effect, status_turn, bounty)
                        VALUES (%s, 100, 50, 0, 10, 0, NULL, 0, 0)
                        """
                    ),
                    (name,),
                )
                player_id = cur.lastrowid
                cur.execute(
                    self._ph(
                        "SELECT player_id, player_name, hp, mp, exp, agility, score, status_effect, status_turn, bounty FROM players WHERE player_id = %s"
                    ),
                    (player_id,),
                )
                new_player = cur.fetchone()
        conn.commit()
        return new_player

    def update_player_status(self, player_id, hp, mp, exp, status_effect=None, status_turn=0):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph(
                    """
                    UPDATE players 
                    SET hp=%s, mp=%s, exp=%s, status_effect=%s, status_turn=%s 
                    WHERE player_id=%s
                    """
                ),
                (hp, mp, exp, status_effect, status_turn, player_id),
            )
        conn.commit()

    def update_bounty(self, player_id, new_bounty):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(self._ph("UPDATE players SET bounty = %s WHERE player_id = %s"), (new_bounty, player_id))
        conn.commit()

    def register_pvp_result(self, battle_id, player_id, point):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(self._ph("UPDATE players SET score = score + %s WHERE player_id = %s"), (point, player_id))
            if battle_id:
                if self.backend == "postgres":
                    cur.execute(
                        """
                        INSERT INTO pvp_results (battle_id, player_id, point)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (battle_id, player_id)
                        DO UPDATE SET point = pvp_results.point + EXCLUDED.point
                        """,
                        (battle_id, player_id, point),
                    )
                else:
                    cur.execute(
                        self._ph(
                            """
                            INSERT INTO pvp_results (battle_id, player_id, point)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (battle_id, player_id)
                            DO UPDATE SET point = COALESCE(pvp_results.point, 0) + excluded.point
                            """
                        ),
                        (battle_id, player_id, point),
                    )
        conn.commit()

    def create_pvp_battle(self, host_player_id):
        conn = self.get_connection()
        with self._cursor() as cur:
            if self.backend == "postgres":
                cur.execute(
                    "INSERT INTO pvp_battles (player_id) VALUES (%s) RETURNING battle_id",
                    (host_player_id,),
                )
                battle_id = cur.fetchone()[0]
            else:
                cur.execute(self._ph("INSERT INTO pvp_battles (player_id) VALUES (%s)"), (host_player_id,))
                battle_id = cur.lastrowid
        conn.commit()
        return battle_id

    def log_pve(self, player_id, monster_name, is_win):
        conn = self.get_connection()
        with self._cursor() as cur:
            monster_id = None
            if monster_name:
                cur.execute(self._ph("SELECT monster_id FROM monsters WHERE monster_name = %s LIMIT 1"), (monster_name,))
                row = cur.fetchone()
                monster_id = row[0] if row else None

            cur.execute(
                self._ph("INSERT INTO pve_logs (player_id, monster_id, is_win) VALUES (%s, %s, %s)"),
                (player_id, monster_id, int(bool(is_win)) if self.backend == "sqlite" else bool(is_win)),
            )
        conn.commit()

    def get_ranking(self):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute("SELECT player_id, player_name, score FROM players ORDER BY score DESC")
            return cur.fetchall()

    def get_player_skills(self, player_id):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph(
                    """
                    SELECT s.skill_id, s.skill_name, s.mp_cost, s.power, s.description, s.is_aoe
                    FROM skills s
                    JOIN player_skills ps ON s.skill_id = ps.skill_id
                    WHERE ps.player_id = %s
                    """
                ),
                (player_id,),
            )
            return cur.fetchall()

    def get_learnable_skills(self, player_id):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph(
                    """
                    SELECT skill_id, skill_name, mp_cost, power, description, is_aoe
                    FROM skills 
                    WHERE skill_id NOT IN (SELECT skill_id FROM player_skills WHERE player_id = %s)
                    ORDER BY RANDOM() 
                    LIMIT 3
                    """
                ),
                (player_id,),
            )
            return cur.fetchall()

    def learn_skill(self, player_id, skill_id):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(self._ph("INSERT INTO player_skills (player_id, skill_id) VALUES (%s, %s)"), (player_id, skill_id))
        conn.commit()

    def get_item_id_by_name(self, item_name):
        with self._cursor() as cur:
            cur.execute(self._ph("SELECT item_id FROM items WHERE item_name = %s LIMIT 1"), (item_name,))
            row = cur.fetchone()
            return row[0] if row else None

    def has_item_effect(self, player_id, effect_type):
        with self._cursor() as cur:
            cur.execute(
                self._ph(
                    """
                    SELECT 1
                    FROM player_items pi
                    JOIN items i ON i.item_id = pi.item_id
                    WHERE pi.player_id = %s AND pi.quantity > 0 AND i.effect_type = %s
                    LIMIT 1
                    """
                ),
                (player_id, effect_type),
            )
            return cur.fetchone() is not None

    def add_item(self, player_id, item_id):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph(
                    """
                    INSERT INTO player_items (player_id, item_id, quantity) 
                    VALUES (%s, %s, 1)
                    ON CONFLICT (player_id, item_id) DO UPDATE SET quantity = player_items.quantity + 1
                    """
                ),
                (player_id, item_id),
            )
        conn.commit()

    def get_player_items(self, player_id, effect_filter=None):
        conn = self.get_connection()
        with self._cursor() as cur:
            sql = """
                SELECT i.item_id, i.item_name, i.rarity, i.effect_type, i.effect_value, i.description, pi.quantity
                FROM items i
                JOIN player_items pi ON i.item_id = pi.item_id
                WHERE pi.player_id = %s AND pi.quantity > 0
            """
            if effect_filter:
                sql += f" AND i.effect_type LIKE '{effect_filter}%'"
            cur.execute(self._ph(sql), (player_id,))
            return cur.fetchall()

    def consume_item(self, player_id, item_id):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph("UPDATE player_items SET quantity = quantity - 1 WHERE player_id = %s AND item_id = %s"),
                (player_id, item_id),
            )
        conn.commit()
    
    def get_items_by_type(self, type_prefix):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(f"SELECT item_id, item_name, rarity FROM items WHERE effect_type LIKE '{type_prefix}%'")
            return cur.fetchall()

    # --- PvPSystem用（生SQLをDBManagerに寄せる） ---
    def get_pvp_participants_raw(self):
        with self._cursor() as cur:
            cur.execute(
                "SELECT player_id, player_name, hp, agility, status_effect, status_turn, exp, mp, score, bounty FROM players WHERE hp > 0"
            )
            return cur.fetchall()

    def get_player_status_row(self, player_id):
        with self._cursor() as cur:
            cur.execute(self._ph("SELECT hp, status_effect, status_turn FROM players WHERE player_id=%s"), (player_id,))
            row = cur.fetchone()
            return row if row else (0, None, 0)

    def get_player_bounty(self, player_id):
        with self._cursor() as cur:
            cur.execute(self._ph("SELECT bounty FROM players WHERE player_id=%s"), (player_id,))
            row = cur.fetchone()
            return row[0] if row else 0

    def update_player_effect(self, player_id, hp, eff, turn):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph("UPDATE players SET hp=%s, status_effect=%s, status_turn=%s WHERE player_id=%s"),
                (hp, eff, turn, player_id),
            )
        conn.commit()

    def damage_player_hp(self, player_id, dmg):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(self._ph("UPDATE players SET hp=hp-%s WHERE player_id=%s"), (dmg, player_id))
        conn.commit()

    def set_player_effect(self, player_id, eff, turn):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(
                self._ph("UPDATE players SET status_effect=%s, status_turn=%s WHERE player_id=%s"),
                (eff, turn, player_id),
            )
        conn.commit()

    def update_player_mp(self, player_id, mp):
        conn = self.get_connection()
        with self._cursor() as cur:
            cur.execute(self._ph("UPDATE players SET mp=%s WHERE player_id=%s"), (mp, player_id))
        conn.commit()

    def get_enemies_list(self, my_id, allow_stealth=False):
        with self._cursor() as cur:
            sql = "SELECT player_id, player_name, hp, status_effect FROM players WHERE hp > 0 AND player_id != %s"
            if not allow_stealth:
                sql += " AND (status_effect IS NULL OR status_effect != '隠密')"
            cur.execute(self._ph(sql), (my_id,))
            rows = cur.fetchall()
        return [{'id': r[0], 'name': r[1], 'hp': r[2], 'effect': r[3]} for r in rows]

    def get_player_name(self, player_id):
        with self._cursor() as cur:
            cur.execute(self._ph("SELECT player_name FROM players WHERE player_id=%s"), (player_id,))
            row = cur.fetchone()
            return row[0] if row else "?"