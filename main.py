# main.py
from db_manager import DBManager
from models import Player
from game_manager import GameManager
from utils import safe_input

def main():
    db = DBManager()
    print("RPG演習 Start")
    
    # ゲーム開始時に全データを初期化（クリーンな状態にする）
    print("🔄 ゲームデータを初期化中...")
    db.reset_all_game_data()
    print("✅ 初期化完了")

    name = safe_input("名前: ")
    player_data = db.get_or_create_player(name)
    player = Player(player_data)

    # 対戦相手（操作可能）を3人作成
    print("👥 対戦相手を作成中...")
    db.ensure_cpu_players(["Player2", "Player3", "Player4"])

    manager = GameManager(player, db)
    # Ctrl+Cは捕まえない（Pythonプログラム自体を停止する）
    manager.run_game_loop()

if __name__ == "__main__":
    main()