# pvp_system.py
import random
import time
from utils import safe_input

class PvPSystem:
    def __init__(self, player, db_manager):
        self.player = player
        self.db = db_manager

    def start_match(self, round_number):
        if not self.player.is_alive(): return
        print(f"\n--- ⚔️ PvP 第{round_number}戦 (バトルロイヤル) ⚔️ ---")

        battle_id = self.db.create_pvp_battle(self.player.id)
        
        participants_data = self._get_participants_raw()
        if len(participants_data) <= 1:
            print("対戦相手がいません...")
            return

        stat_map = {}
        
        for p in participants_data:
            pid = p[0]
            stat_map[pid] = {'atk': 0, 'def': 0, 'spd': 0, 'score_rate': 1.0, 'bounty': p[9]}
            
            p_items = self.db.get_player_items(pid, "pvp_")
            
            if pid == self.player.id and p_items:
                print("\n🎒 PvPアイテム使用:")
            
            for item in p_items:
                i_id, i_name, i_type, i_val = item[0], item[1], item[3], item[4]
                if i_type == "pvp_atk":
                    stat_map[pid]['atk'] += i_val
                    if pid == self.player.id: print(f"  ⚔️ {i_name} 消費 -> 攻撃力+{i_val}")
                elif i_type == "pvp_def":
                    stat_map[pid]['def'] += i_val
                    if pid == self.player.id: print(f"  🛡️ {i_name} 消費 -> 防御力+{i_val}")
                elif i_type == "pvp_spd":
                    stat_map[pid]['spd'] += i_val
                    if pid == self.player.id: print(f"  👟 {i_name} 消費 -> 素早さ+{i_val}")
                elif i_type == "pvp_score":
                    stat_map[pid]['score_rate'] = float(i_val)
                    if pid == self.player.id: print(f"  💍 {i_name} 消費 -> スコア {i_val}倍")
                self.db.consume_item(pid, i_id)
            
            if pid == self.player.id and p_items: print("")

        dead_record = []
        # 懸賞金（賞金首）討伐ボーナスはここに集計し、順位ポイント付与時に“勝ち残り順を崩さない範囲で”加算する
        bounty_bonus = {}
        turn_count = 0
        
        while True:
            turn_count += 1
            living_count = self._count_living_players(participants_data)
            if living_count <= 1: break

            print(f"\n--- Turn {turn_count} (生存: {living_count}人) ---")
            
            # Agilityが高い順、同値ならIDが小さい順（プレイヤー優先）
            turn_order = sorted(participants_data, key=lambda x: (x[3] + stat_map[x[0]]['spd'], -x[0]), reverse=True)

            for p_data in turn_order:
                actor_id, actor_name, actor_exp = p_data[0], p_data[1], p_data[6]
                
                hp, eff, turn = self._get_status(actor_id)
                if hp <= 0:
                    if actor_id not in dead_record: dead_record.append(actor_id)
                    continue

                # 神の加護: 自分のターン開始時にHP+10（PvE/PvP）
                if actor_id == self.player.id and self.db.has_item_effect(self.player.id, "bless_regen"):
                    max_hp = 100 + (self.player.level * 10)
                    healed = min(max_hp, hp + 10)
                    if healed != hp:
                        diff = healed - hp
                        hp = healed
                        self.player.hp = healed
                        self._update_status(actor_id, hp, eff, turn)
                        print(f"✨ 神の加護: {actor_name} のHPが {diff} 回復した！ (HP: {hp})")

                actor_lvl = (actor_exp // 100) + 1
                base_atk = 10 + (actor_lvl * 5)
                final_atk = base_atk + stat_map[actor_id]['atk']

                skip_turn = False
                if eff in ["氷結", "気絶"]:
                    print(f"❄️ {actor_name} は {eff} で動けない！")
                    skip_turn = True
                
                if turn > 0:
                    turn -= 1
                    if turn == 0:
                        print(f"✨ {actor_name} の {eff} が切れた！")
                        eff = None
                    self._update_status(actor_id, hp, eff, turn)

                if skip_turn: continue

                if actor_id == self.player.id:
                    self._manual_turn(actor_id, actor_name, final_atk, hp, stat_map, is_me=True)
                else:
                    self._manual_turn(actor_id, actor_name, final_atk, hp, stat_map, is_me=False)
                
                self._check_deaths_and_bounty(actor_id, actor_name, participants_data, dead_record, stat_map, bounty_bonus)

        # バトルが完全に終了したタイミングで1回だけスコアを確定・加算する
        self._calculate_score_and_update_bounty(
            battle_id,
            participants_data,
            dead_record,
            stat_map[self.player.id]['score_rate'],
            round_number,
            bounty_bonus,
        )

    def _get_participants_raw(self):
        return self.db.get_pvp_participants_raw()

    def _count_living_players(self, participants):
        count = 0
        for p in participants:
            hp, _, _ = self._get_status(p[0])
            if hp > 0: count += 1
        return count

    def _check_deaths_and_bounty(self, attacker_id, attacker_name, participants, dead_record, stat_map, bounty_bonus):
        for p in participants:
            pid = p[0]
            if pid in dead_record: continue
            
            hp, _, _ = self._get_status(pid)
            if hp <= 0:
                target_name = p[1]
                print(f"💀 {target_name} は力尽きた...")
                dead_record.append(pid)

                target_bounty = stat_map[pid]['bounty']
                if target_bounty > 0:
                    print(f"💰 {attacker_name} が賞金首 {target_name} を討ち取った！ (+{target_bounty}pt)")
                    bounty_bonus[attacker_id] = bounty_bonus.get(attacker_id, 0) + int(target_bounty)

    def _manual_turn(self, pid, name, atk, hp, stat_map, is_me=False):
        # 自分のMPはself.player.mpで持っているが、他人のMPはDBから取る必要がある
        # 統一するため、常にDBから最新状態を取得する
        row = self.db.get_or_create_player(name) # nameから取得
        # row: id, name, hp, mp, exp, agi, score, eff, turn, bounty
        current_mp = row[3]

        print(f"\n👉 {name} の番 (HP:{hp}, MP:{current_mp})")
        skills = self.db.get_player_skills(pid)
        print("0. 通常攻撃")
        for i, s in enumerate(skills): 
            aoe = "[全体]" if s[5] else ""
            print(f"{i+1}.{s[1]}{aoe}(MP:{s[2]}, {s[3]}%)")

        try: 
            act_str = safe_input(">> ")
            act = int(act_str)
        except ValueError: act = 0
        

        damage = 0
        apply_eff = None
        is_aoe = False
        target = None

        # スキル選択後に、必要なら対象を選ぶ
        selected_skill = None
        if 1 <= act <= len(skills):
            selected_skill = skills[act - 1]
            is_aoe = bool(selected_skill[5])

        # 対象が必要な行動: 通常攻撃 / 単体攻撃スキル
        need_target = (act == 0) or (selected_skill is not None and not is_aoe and selected_skill[1] not in ["ヒール", "隠れ身"])

        enemies = None
        if need_target:
            enemies = self._get_enemies_list(pid, allow_stealth=False)
            if not enemies:
                print("  (攻撃できる相手がいません...)")
                return

            print("攻撃対象:")
            for i, r in enumerate(enemies):
                st = f"[{r['effect']}]" if r['effect'] else ""
                bounty = stat_map[r['id']]['bounty']
                b_mark = f" [👑{bounty}pt]" if bounty > 0 else ""
                print(f"  {i+1}. {r['name']} (HP:{r['hp']}) {st}{b_mark}")

            try:
                t_idx_str = safe_input("  対象番号>> ")
                t_idx = int(t_idx_str)
                if 1 <= t_idx <= len(enemies):
                    target = enemies[t_idx - 1]
            except ValueError:
                pass
            if not target:
                target = enemies[0]

        # 攻撃行動を行う場合は、隠密を解除
        # DB上のステータスを確認
        eff, turn = row[7], row[8]
        
        if eff == "隠密" and act != 0 and selected_skill is not None and selected_skill[1] == "隠れ身":
            pass
        elif eff == "隠密" and (act == 0 or selected_skill is not None):
            self._set_effect(pid, None, 0)
            print("  (行動のため隠密を解除しました)")
            if is_me:
                self.player.status_effect = None
                self.player.status_turn = 0

        if act == 0:
            damage = int(atk * random.uniform(0.9, 1.1))
            print(f"  ⚔️ {name} の通常攻撃 -> {target['name']} (威力:{damage})")
        elif selected_skill is not None:
            s_name, s_mp, s_power, _ = selected_skill[1], selected_skill[2], selected_skill[3], selected_skill[5]
            if current_mp < s_mp:
                print(f"  MP不足！{name} は通常攻撃を行います。")
                # 直前の行動が全体攻撃などでtarget未選択のケースがあるため、通常攻撃用に対象を確保する
                if target is None:
                    fallback_enemies = enemies if enemies is not None else self._get_enemies_list(pid, allow_stealth=False)
                    if not fallback_enemies:
                        print("  (攻撃できる相手がいません...)")
                        return
                    target = fallback_enemies[0]
                damage = int(atk * random.uniform(0.9, 1.1))
                print(f"  ⚔️ {name} の通常攻撃 -> {target['name']} (威力:{damage})")
            else:
                # MP消費
                new_mp = current_mp - s_mp
                self.db.update_player_mp(pid, new_mp)
                if is_me: self.player.mp = new_mp

                if s_name == "隠れ身":
                    self._set_effect(pid, "隠密", 1)
                    print(f"  🥷 {name} は {s_name} を発動！ (敵から狙われなくなった)")
                    if is_me:
                        self.player.status_effect = "隠密"
                        self.player.status_turn = 1
                    return

                if s_name == "ヒール":
                    heal_amount = int(atk * 2)
                    # HP回復処理
                    # 現在HPを取得しなおす
                    now_hp, now_eff, now_turn = self._get_status(pid)
                    new_hp = now_hp + heal_amount
                    self._update_status(pid, new_hp, now_eff, now_turn)
                    print(f"  ✨ {name} は自分に {s_name} を発動！ (HP {heal_amount} 回復 -> {new_hp})")
                    if is_me: self.player.hp += heal_amount
                    return

                base = atk * (s_power / 100)
                damage = int(base * random.uniform(0.9, 1.1))
                damage, apply_eff = self._apply_skill_effect(s_name, damage)

                if is_aoe:
                    print(f"  🌏 {name} は {s_name} を発動！ (全体 / 威力:{damage})")
                else:
                    print(f"  ✨ {name} は {s_name} を発動 -> {target['name']} (威力:{damage})")

                if s_name == "ドレイン":
                    # ドレイン回復
                    heal_val = damage // 2
                    now_hp, now_eff, now_turn = self._get_status(pid)
                    new_hp = now_hp + heal_val
                    self._update_status(pid, new_hp, now_eff, now_turn)
                    print(f"  🧛 {name} はドレインでHPを吸収！ (自身のHP {heal_val} 回復 -> {new_hp})")
                    if is_me: self.player.hp += heal_val

        # ダメージ適用
        if is_aoe:
            aoe_enemies = self._get_enemies_list(pid, allow_stealth=False)
            for enemy in aoe_enemies:
                if damage > 0:
                    enemy_def = stat_map[enemy['id']]['def']
                    final_dmg = max(1, damage - enemy_def)
                    self._damage_player(enemy['id'], final_dmg)
                    print(f"    -> {enemy['name']} に {final_dmg} ダメージ！ (防:{enemy_def})")
                    if apply_eff:
                        self._set_effect(enemy['id'], apply_eff[0], apply_eff[1])
                        print(f"    -> {enemy['name']} は {apply_eff[0]} になった！")
        elif target and damage > 0:
            enemy_def = stat_map[target['id']]['def']
            final_dmg = max(1, damage - enemy_def)
            self._damage_player(target['id'], final_dmg)
            print(f"    -> {target['name']} に {final_dmg} ダメージ！ (防御減算: -{enemy_def})")
            if apply_eff:
                self._set_effect(target['id'], apply_eff[0], apply_eff[1])
                print(f"    -> {target['name']} は {apply_eff[0]} になった！")

    def _cpu_turn(self, pid, name, atk, stat_map):
        # 廃止されたが、念のため残すか、あるいは削除
        pass

    def _calculate_score_and_update_bounty(self, battle_id, participants, dead_record, my_multiplier, round_number, bounty_bonus):
        rank_order = list(dead_record)
        for p in participants:
            if p[0] not in rank_order:
                rank_order.append(p[0])
        
        # 順位ごとのポイント定義 (1位, 2位, 3位, 4位...)
        rank_points = [100, 60, 30, 10]
        
        multiplier = 1
        if round_number == 2: multiplier = 2
        elif round_number == 3: multiplier = 5

        print(f"\n📊 バトル終了！ 順位ポイント (倍率 x{multiplier}):")
        
        survivor_id = rank_order[-1] if rank_order else None

        # 1位から順に表示するために逆順にする
        display_order = list(reversed(rank_order))

        prev_awarded = None
        for i, pid in enumerate(display_order):
            rank = i + 1
            
            # ランクに基づいてポイントを決定
            if i < len(rank_points):
                pt = rank_points[i] * multiplier
            else:
                pt = 10 * multiplier # 5位以降は一律10pt
            
            final_pt = pt
            item_effect_msg = ""
            if pid == self.player.id:
                final_pt = int(pt * my_multiplier)
                if my_multiplier > 1.0:
                    item_effect_msg = f" (アイテム効果 x{int(my_multiplier)})"

            # 懸賞金討伐ボーナスを加算（ただし“勝ち残り順のスコア序列”を崩さないように調整）
            bonus = int(bounty_bonus.get(pid, 0))
            bonus_msg = ""
            if bonus > 0:
                adjusted = bonus
                if prev_awarded is not None:
                    # 上位の付与ポイントを超えない（同点まで許可）
                    adjusted = min(adjusted, max(0, prev_awarded - final_pt))
                if adjusted > 0:
                    final_pt += adjusted
                    bonus_msg = f" +賞金{adjusted}pt"
                else:
                    bonus_msg = " (賞金ptは順位維持のため加算なし)"
            
            p_name = self._get_name(pid)
            print(f"  {rank}位: {p_name} (+{final_pt}pt{bonus_msg}){item_effect_msg}")
            self.db.register_pvp_result(battle_id, pid, final_pt)
            prev_awarded = final_pt

            if pid == survivor_id:
                current = self._get_bounty(pid)
                new_bounty = min(50, current + 10)
                self.db.update_bounty(pid, new_bounty)
                print(f"    👑 賞金首ボーナス！ {p_name} の懸賞金が {new_bounty}pt にアップ！")
            else:
                self.db.update_bounty(pid, 0)

    def _apply_skill_effect(self, name, damage):
        if name == "ブリザード": return (damage, ("氷結", 1)) if random.random() < 0.3 else (damage, None)
        if name == "ポイズン": return (damage, ("毒", 3))
        if name == "スタン撃ち": return (damage, ("気絶", 1)) if random.random() < 0.5 else (damage, None)
        return (damage, None)

    def _get_status(self, pid):
        return self.db.get_player_status_row(pid)

    def _get_bounty(self, pid):
        return self.db.get_player_bounty(pid)

    def _update_status(self, pid, hp, eff, turn):
        self.db.update_player_effect(pid, hp, eff, turn)

    def _damage_player(self, pid, dmg):
        self.db.damage_player_hp(pid, dmg)

    def _set_effect(self, pid, eff, turn):
        self.db.set_player_effect(pid, eff, turn)

    def _update_me(self):
        self._update_status(self.player.id, self.player.hp, self.player.status_effect, self.player.status_turn)
        self.db.update_player_mp(self.player.id, self.player.mp)

    def _get_enemies_list(self, my_id, allow_stealth=False):
        return self.db.get_enemies_list(my_id, allow_stealth=allow_stealth)

    def _get_name(self, pid):
        return self.db.get_player_name(pid)