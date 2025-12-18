# models.py
from config import LEVEL_UP_EXP

class Player:
    def __init__(self, data):
        self.id = data[0]
        self.name = data[1]
        self.hp = data[2]
        self.mp = data[3]
        self.exp = data[4]
        self.agility = data[5] if len(data) > 5 else 10
        self.level = (self.exp // LEVEL_UP_EXP) + 1
        self.status_effect = data[7] if len(data) > 7 else None
        self.status_turn = data[8] if len(data) > 8 else 0

    @property
    def attack_power(self):
        return 10 + (self.level * 5)

    def add_exp(self, amount):
        old_level = self.level
        self.exp += amount
        self.level = (self.exp // LEVEL_UP_EXP) + 1
        print(f"✨ {self.name} は経験値を {amount} 獲得した！ (Total: {self.exp})")
        return self.level > old_level

    def is_alive(self):
        return self.hp > 0

class Monster:
    def __init__(self, name, hp, attack, agility):
        self.name = name
        self.hp = hp
        self.attack = attack
        self.agility = agility
        self.status_effect = None
        self.status_turn = 0