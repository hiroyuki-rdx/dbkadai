# game_manager.py
import random
from pve_system import PvESystem
from pvp_system import PvPSystem
from config import GAME_LOOP_COUNT, LEVEL_UP_EXP
from utils import safe_input

class GameManager:
    def __init__(self, player, db_manager):
        self.player = player
        self.db = db_manager
        self.pve = PvESystem(player, db_manager)
        self.pvp = PvPSystem(player, db_manager)

    def run_game_loop(self):
        print("\n=== 初期ボーナス ===")
        print("1. 経験値+100 (即レベルアップ)  2. 神の加護  9. [デバッグ] 最強セット")
        c = safe_input(">> ")
        if c == "1": 
            self.player.add_exp(100)
            self.db.update_player_status(self.player.id, self.player.hp, self.player.mp, self.player.exp)
            self.pve._process_level_up()
        elif c == "2":
            bless_id = self.db.get_item_id_by_name("神の加護")
            if bless_id:
                self.db.add_item(self.player.id, bless_id)
                print("✅ 神の加護を授かりました！（PvE/PvPで毎ターンHP+10）")
        elif c == "9":
            print("🔧 デバッグモード: レベルアップ & 全アイテム付与")
            self.player.add_exp(500) # Lv.6程度
            self.db.update_player_status(self.player.id, self.player.hp, self.player.mp, self.player.exp)
            self.pve._process_level_up()
            
            # 神の加護
            bless_id = self.db.get_item_id_by_name("神の加護")
            if bless_id: self.db.add_item(self.player.id, bless_id)
            
            # PvP用アイテムをいくつか付与
            items = self.db.get_items_by_type("pvp_")
            for item in items:
                self.db.add_item(self.player.id, item[0])
            print("✅ 最強セットを適用しました")

        self._show_ranking()

        # 改定ルール: PvE→PvP を1セットとして3回行う
        for i in range(1, GAME_LOOP_COUNT + 1):
            print(f"\n{'='*15} 第 {i} 戦 {'='*15}")

            print(f"\n--- 🏟️ PvE 第{i}戦（モンスター戦） ---")
            self.pve.start_farm()
            self._full_recovery()

            print(f"\n--- ⚔️ PvP 第{i}戦 ---")
            self.pvp.start_match(i)
            self._full_recovery()

            self._distribute_loser_items()
            self._show_ranking()

        self._show_final_result()

    def _distribute_loser_items(self):
        ranking = self.db.get_ranking()
        if len(ranking) < 2: return

        losers = ranking[-2:]
        gift_list = self.db.get_items_by_type("pve_")
        if not gift_list: return

        print("\n🎁 --- 敗者救済タイム ---")
        for loser in losers:
            l_id, l_name = loser[0], loser[1]
            weights = []
            for item in gift_list:
                rar = item[2]
                if rar==1: w=60
                elif rar==2: w=30
                else: w=10
                weights.append(w)
            
            gift = random.choices(gift_list, weights=weights, k=1)[0]
            self.db.add_item(l_id, gift[0])
            
            star = "★" * gift[2]
            if l_id == self.player.id:
                print(f"  順位が低いため、支援物資「{gift[1]} ({star})」を受け取りました！")
            else:
                print(f"  {l_name} に支援物資が送られました。")

    def _full_recovery(self):
        # 全プレイヤーを全回復（次のPvE/PvPに全員が参加できるようにする）
        self.db.full_recover_all_players(LEVEL_UP_EXP)

        # 手元のプレイヤーオブジェクトも同期
        max_hp = 100 + (self.player.level * 10)
        self.player.hp = max_hp
        self.player.mp = 50
        self.player.status_effect = None
        self.player.status_turn = 0
        print(f"(全員回復: HP/MP/状態異常 - MaxHP:{max_hp})")

    def _show_ranking(self):
        print("\n📊 暫定順位")
        ranking = self.db.get_ranking()
        current_rank = 1
        for i, r in enumerate(ranking):
            # 前の人と同点なら同じ順位
            if i > 0 and r[2] == ranking[i-1][2]:
                display_rank = current_rank
            else:
                display_rank = i + 1
                current_rank = display_rank
            print(f"  {display_rank}位: {r[1]} ({r[2]}pt)")

    def _show_final_result(self):
        print("\n👑 最終結果")
        for idx, r in enumerate(self.db.get_ranking()):
            print(f"{idx+1}位: {r[1]} ({r[2]}pt)")