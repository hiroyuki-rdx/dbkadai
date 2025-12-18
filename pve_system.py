# pve_system.py
import random
from models import Monster
from utils import safe_input
 
class PvESystem:
    def __init__(self, player, db_manager):
        self.player = player
        self.db = db_manager

    def start_player_battle_4(self):
        print("\n--- 🏟️ 最終PvE: プレイヤー4人対戦 🏟️ ---")

        participants = self.db.get_pvp_participants_raw()
        if len(participants) < 4:
            print("参加者が4人未満のため開始できません...")
            return

        me = None
        others = []
        for p in participants:
            if p[0] == self.player.id:
                me = p
            else:
                others.append(p)
        if me is None:
            print("あなたが参加者に見つかりません...")
            return

        if len(others) < 3:
            print("対戦相手が足りません...")
            return

        chosen = [me] + random.sample(others, k=3)

        dead_record = []
        turn_count = 0
        max_turn = 20

        while True:
            turn_count += 1
            living = self._count_living_in_list(chosen)
            if living <= 1:
                break
            if turn_count > max_turn:
                print("\n⌛ タイムアップ！")
                break

            print(f"\n--- Turn {turn_count} (生存: {living}人) ---")

            # agilityで行動順（固定ステータス）
            turn_order = sorted(chosen, key=lambda x: x[3], reverse=True)

            for p_data in turn_order:
                pid, name, _, agi, _, _, exp, _, _, _ = p_data

                hp, eff, eff_turn = self.db.get_player_status_row(pid)
                if hp <= 0:
                    if pid not in dead_record:
                        dead_record.append(pid)
                    continue

                # 状態異常の経過
                skip_turn = False
                if eff in ["氷結", "気絶"]:
                    print(f"❄️ {name} は {eff} で動けない！")
                    skip_turn = True

                if eff_turn > 0:
                    eff_turn -= 1
                    if eff_turn == 0:
                        eff = None
                    self.db.update_player_effect(pid, hp, eff, eff_turn)

                # 神の加護: 自分のターン開始時にHP+10
                if pid == self.player.id and self.db.has_item_effect(self.player.id, "bless_regen"):
                    max_hp = 100 + (self.player.level * 10)
                    healed = min(max_hp, hp + 10)
                    if healed != hp:
                        diff = healed - hp
                        hp = healed
                        self.player.hp = healed
                        self.db.update_player_effect(pid, hp, eff, eff_turn)
                        print(f"✨ 神の加護: HPが {diff} 回復した！ (HP: {hp})")

                if skip_turn:
                    continue

                lvl = (exp // 100) + 1
                atk = 10 + (lvl * 5)

                if pid == self.player.id:
                    self._player_turn_pve_pvp(atk, chosen)
                else:
                    self._cpu_turn_pve_pvp(pid, name, atk, chosen)

                # 戦闘不能チェック
                for q in chosen:
                    qid = q[0]
                    qhp, _, _ = self.db.get_player_status_row(qid)
                    if qhp <= 0 and qid not in dead_record:
                        print(f"💀 {self.db.get_player_name(qid)} は力尽きた...")
                        dead_record.append(qid)

        # 順位確定（死んだ順 + 最後に生存者）
        rank_order = list(dead_record)
        for p in chosen:
            if p[0] not in rank_order:
                rank_order.append(p[0])

        # 自分の順位に応じて経験値
        exp_by_rank = [10, 30, 60, 100]  # 4位→10, 3位→30, 2位→60, 1位→100
        my_rank_idx = None
        for i, pid in enumerate(rank_order):
            if pid == self.player.id:
                my_rank_idx = i
                break

        if my_rank_idx is not None:
            # rank_orderは「脱落順」なので、インデックスが小さいほど順位が低い
            # 4人の場合: i=0が4位, i=3が1位
            award = exp_by_rank[min(my_rank_idx, 3)]
            print(f"\n🏆 最終PvE結果: あなたは {my_rank_idx+1}番目に決着（経験値+{award}）")
            if self.player.add_exp(award):
                self._process_level_up()
            self._update_db()
            self.db.log_pve(self.player.id, "プレイヤー対戦", True)
        else:
            self.db.log_pve(self.player.id, "プレイヤー対戦", False)

    def _count_living_in_list(self, participants):
        count = 0
        for p in participants:
            hp, _, _ = self.db.get_player_status_row(p[0])
            if hp > 0:
                count += 1
        return count

    def _pick_targets_from_chosen(self, my_id, chosen):
        targets = []
        for p in chosen:
            pid = p[0]
            if pid == my_id:
                continue
            hp, eff, _ = self.db.get_player_status_row(pid)
            if hp <= 0:
                continue
            if eff == "隠密":
                continue
            targets.append((pid, self.db.get_player_name(pid), hp, eff))
        return targets

    def _player_turn_pve_pvp(self, atk, chosen):
        hp, _, _ = self.db.get_player_status_row(self.player.id)
        self.player.hp = hp
        print(f"\n👉 あなた ({self.player.name}) の番 (HP:{self.player.hp}, MP:{self.player.mp})")
        skills = self.db.get_player_skills(self.player.id)
        print("0. 通常攻撃")
        for i, s in enumerate(skills):
            aoe = "[全体]" if s[5] else ""
            print(f"{i+1}.{s[1]}{aoe}(MP:{s[2]}, {s[3]}%)")

        try:
            act = int(input(">> "))
        except:
            act = 0


        damage = 0
        apply_eff = None
        is_aoe = False
        target = None

        selected_skill = None
        if 1 <= act <= len(skills):
            selected_skill = skills[act - 1]
            is_aoe = bool(selected_skill[5])

        need_target = (act == 0) or (selected_skill is not None and not is_aoe and selected_skill[1] not in ["ヒール", "隠れ身"])

        targets = None
        if need_target:
            targets = self._pick_targets_from_chosen(self.player.id, chosen)
            if not targets:
                print("  (攻撃できる相手がいません...)")
                return

            print("攻撃対象:")
            for i, t in enumerate(targets):
                st = f"[{t[3]}]" if t[3] else ""
                print(f"  {i+1}. {t[1]} (HP:{t[2]}) {st}")

            try:
                t_idx = int(input("  対象番号>> "))
                if 1 <= t_idx <= len(targets):
                    target = targets[t_idx - 1]
            except:
                pass
            if not target:
                target = targets[0]

        if act == 0:
            damage = int(atk * random.uniform(0.9, 1.1))
            print(f"  ⚔️ 通常攻撃 -> {target[1]} (威力:{damage})")
        elif selected_skill is not None:
            s_name, s_mp, s_power, _ = selected_skill[1], selected_skill[2], selected_skill[3], selected_skill[5]
            if self.player.mp < s_mp:
                print("  MP不足！")
                return

            self.player.mp -= s_mp
            self.db.update_player_mp(self.player.id, self.player.mp)

            if s_name == "隠れ身":
                self.player.status_effect = "隠密"
                self.player.status_turn = 1
                self.db.set_player_effect(self.player.id, "隠密", 1)
                print("  🥷 隠れ身！ (敵から狙われなくなった)")
                return

            if s_name == "ヒール":
                self.player.hp += int(atk * 2)
                self.db.update_player_effect(self.player.id, self.player.hp, self.player.status_effect, self.player.status_turn)
                print(f"  ✨ {s_name}！ (HP回復)")
                return

            base = atk * (s_power / 100)
            damage = int(base * random.uniform(0.9, 1.1))
            damage, apply_eff = self._calc_skill_dmg(s_name, s_power)

            if is_aoe:
                print(f"  🌏 {s_name}！ (全体 / 威力:{damage})")
            else:
                print(f"  ✨ {s_name} -> {target[1]} (威力:{damage})")

            if s_name == "ドレイン":
                self.player.hp += damage // 2
                self.db.update_player_effect(self.player.id, self.player.hp, self.player.status_effect, self.player.status_turn)

        if is_aoe:
            if targets is None:
                targets = self._pick_targets_from_chosen(self.player.id, chosen)
            for pid, name, thp, teff in targets:
                if damage <= 0:
                    continue
                self.db.damage_player_hp(pid, damage)
                print(f"    -> {name} に {damage} ダメージ！")
                if apply_eff:
                    self.db.set_player_effect(pid, apply_eff[0], apply_eff[1])
        else:
            if target and damage > 0:
                self.db.damage_player_hp(target[0], damage)
                print(f"    -> {target[1]} に {damage} ダメージ！")
                if apply_eff:
                    self.db.set_player_effect(target[0], apply_eff[0], apply_eff[1])
                    print(f"    -> {target[1]} は {apply_eff[0]} になった！")

    def _cpu_turn_pve_pvp(self, pid, name, atk, chosen):
        targets = self._pick_targets_from_chosen(pid, chosen)
        if not targets:
            return
        tgt = random.choice(targets)
        dmg = int(atk * random.uniform(0.9, 1.1))
        print(f"\n🤖 {name} の番 -> {tgt[1]} に攻撃 ({dmg} dmg)")
        self.db.damage_player_hp(tgt[0], dmg)
        if tgt[0] == self.player.id:
            self.player.hp -= dmg
 
    def start_farm(self):
        print("\n--- 🌲 ファームフェーズ 🌲 ---")
       
        bonus_exp_rate = 1.0
        bonus_dmg_rate = 1.0
        items = self.db.get_player_items(self.player.id, "pve_")
        if items:
            print("\n🎒 アイテムを使用（このターンのみ有効）:")
            for item in items:
                i_id, i_name, i_val = item[0], item[1], item[4]
                if item[3] == "pve_heal":
                    old_hp = self.player.hp
                    self.player.hp = min(self.player.hp + i_val, 100 + (self.player.level*10))
                    diff = self.player.hp - old_hp
                    print(f"  💊 {i_name} 消費 -> HP {diff} 回復 (HP: {self.player.hp})")
                elif item[3] == "pve_exp":
                    bonus_exp_rate += (i_val / 100)
                    print(f"  📚 {i_name} 消費 -> 経験値アップ")
                elif item[3] == "pve_dmg":
                    bonus_dmg_rate += (i_val / 100)
                    print(f"  ⚔️ {i_name} 消費 -> ダメージアップ")
                self.db.consume_item(self.player.id, i_id)
            print("")
 
        # (名前, HP, 攻撃力, Agility, EXP)
        monsters = [
            ("スライム", 30, 10, 5, 10), ("ゴブリン", 50, 15, 12, 50),
            ("ドラゴン", 150, 30, 20, 100), ("魔王の影", 300, 50, 40, 200)
        ]
        for i, m in enumerate(monsters):
            print(f"  {i+1}. {m[0]} (HP:{m[1]}, ATK:{m[2]}, AGI:{m[3]}, EXP:{m[4]})")
       
        monster = None
        win_exp = 0
        while True:
            try:
                c_str = safe_input(">> ")
                c = int(c_str)
                if 1 <= c <= len(monsters):
                    d = monsters[c-1]
                    monster = Monster(d[0], d[1], d[2], d[3])
                    win_exp = d[4]
                    break
            except ValueError: pass
 
        print(f"\nBattle Start: {monster.name} (HP:{monster.hp}, AGI:{monster.agility}) vs You (AGI:{self.player.agility})")
       
        while monster.hp > 0 and self.player.is_alive():
            # 行動順決定: ルール変更によりプレイヤーが必ず先攻
            turn_order = [("player", self.player), ("monster", monster)]

            for p_type, actor in turn_order:
                if monster.hp <= 0 or not self.player.is_alive(): break

                # 状態異常チェック
                skip_turn = False
                if actor.status_effect in ["氷結", "気絶"]:
                    print(f"❄️ {actor.name if p_type=='monster' else 'あなた'} は {actor.status_effect} で動けない！")
                    skip_turn = True
                
                if actor.status_effect == "毒":
                    actor.hp -= 10
                    print(f"☠️ {actor.name if p_type=='monster' else 'あなた'} に毒ダメージ！ (HP: {actor.hp})")

                if actor.status_turn > 0:
                    actor.status_turn -= 1
                    if actor.status_turn == 0:
                        print(f"✨ {actor.name if p_type=='monster' else 'あなた'} の {actor.status_effect} が切れた！")
                        actor.status_effect = None
                
                if actor.hp <= 0: continue

                if skip_turn: continue

                if p_type == "player":
                    # --- プレイヤーのターン ---
                    if self.db.has_item_effect(self.player.id, "bless_regen"):
                        max_hp = 100 + (self.player.level * 10)
                        old_hp = self.player.hp
                        self.player.hp = min(max_hp, self.player.hp + 10)
                        if self.player.hp > old_hp:
                            print(f"✨ 神の加護: HPが {self.player.hp - old_hp} 回復した！ (HP: {self.player.hp})")

                    atk = self.player.attack_power
                    print(f"\nあなたのターン (Lv.{self.player.level} 攻:{atk}, HP:{self.player.hp}, MP:{self.player.mp})")
                
                    my_skills = self.db.get_player_skills(self.player.id)
                    print("0. 通常攻撃 (100%)")
                    for i, s in enumerate(my_skills):
                        aoe = "[全体]" if s[5] else ""
                        print(f"{i+1}. {s[1]}{aoe} (MP:{s[2]}, 威力:{s[3]}%)")
                
                    try: 
                        act_str = safe_input(">> ")
                        act = int(act_str)
                    except ValueError: act = 0
    
                    damage = 0
                    effect = None
                
                    if act == 0:
                        base_dmg = self.player.attack_power
                        damage = int(base_dmg * random.uniform(0.9, 1.1))
                    elif 1 <= act <= len(my_skills):
                        s = my_skills[act-1]
                        if self.player.mp >= s[2]:
                            self.player.mp -= s[2]
                            damage, effect = self._calc_skill_dmg(s[1], s[3])
                            
                            if s[1] == "ヒール": 
                                heal_val = int(self.player.attack_power*2)
                                self.player.hp += heal_val
                                print(f"  ✨ {s[1]}！ (HP {heal_val} 回復 -> {self.player.hp})")
                            elif s[1] == "ドレイン": 
                                heal_val = damage//2
                                self.player.hp += heal_val
                                print(f"  🧛 ドレイン！ (HP {heal_val} 吸収 -> {self.player.hp})")
                            elif s[1] == "隠れ身": print("  (気配を消した！)")
                            
                            if effect:
                                monster.status_effect = effect[0]
                                monster.status_turn = effect[1]
                        else:
                            print("MP不足！通常攻撃を行います。")
                            base_dmg = self.player.attack_power
                            damage = int(base_dmg * random.uniform(0.9, 1.1))
                    
                    damage = int(damage * bonus_dmg_rate)
                    if damage > 0:
                        print(f"  ⚔️ ダメージ: {damage}")
                        monster.hp -= damage

                else:
                    # --- モンスターのターン ---
                    dmg = monster.attack
                    self.player.hp -= dmg
                    # ダメージを受けたら即座にDBへ反映（強制終了対策）
                    self._update_db()
                    print(f"\n💀 {monster.name} の攻撃！ {dmg} ダメージ (残りHP: {self.player.hp})")

            # 決着判定
            if monster.hp <= 0:
                final_exp = int(win_exp * bonus_exp_rate)
                print(f"🏆 勝利！ EXP+{final_exp}")
                if self.player.add_exp(final_exp):
                    self._process_level_up()
                self._check_drop()
                self.db.log_pve(self.player.id, monster.name, True)
                self._update_db()
                break
            
            if not self.player.is_alive():
                print("☠️ 敗北...")
                self.db.log_pve(self.player.id, monster.name, False)
                self._update_db()
                break
 
    def _calc_skill_dmg(self, name, power_pct):
        base = self.player.attack_power * (power_pct / 100)
        dmg = int(base * random.uniform(0.9, 1.1))
        if name == "ブリザード": return (dmg, ("氷結", 1)) if random.random() < 0.3 else (dmg, None)
        if name == "ポイズン": return (dmg, ("毒", 3))
        if name == "スタン撃ち": return (dmg, ("気絶", 1)) if random.random() < 0.5 else (dmg, None)
        if name == "全力斬り": return (dmg, None) if random.random() < 0.7 else (0, None)
        if name == "隠れ身": return (0, None)
        return (dmg, None)
 
    def _process_level_up(self):
        print("\n🎉 レベルアップ！")
        cands = self.db.get_learnable_skills(self.player.id)
        if not cands: return
        for i, s in enumerate(cands):
            aoe = "[全体]" if s[5] else ""
            print(f"  {i+1}: {s[1]}{aoe} (MP:{s[2]}, 威力:{s[3]}%)")
        try:
            c_str = safe_input(">> ")
            c = int(c_str)
            if 1<=c<=len(cands):
                self.db.learn_skill(self.player.id, cands[c-1][0])
                print(f"✅ {cands[c-1][1]} 習得！")
        except ValueError: pass
 
    def _check_drop(self):
        drop_list = self.db.get_items_by_type("pvp_")
        if not drop_list: return
 
        if random.random() < 0.4:
            weights = []
            for item in drop_list:
                rar = item[2]
                if rar == 1: w = 60
                elif rar == 2: w = 30
                elif rar == 3: w = 9
                else: w = 1
                weights.append(w)
           
            dropped = random.choices(drop_list, weights=weights, k=1)[0]
            self.db.add_item(self.player.id, dropped[0])
            star = "★" * dropped[2]
            print(f"\n🎁 {star}「{dropped[1]}」をドロップ！(次のPvPで使用されます)")
 
    def _update_db(self):
        self.db.update_player_status(self.player.id, self.player.hp, self.player.mp, self.player.exp, self.player.status_effect, self.player.status_turn)
 