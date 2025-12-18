# create_player.py
import argparse
from db_manager import DBManager

def main():
    parser = argparse.ArgumentParser(description="新しいプレイヤーを作成します")
    parser.add_argument("--player_name", required=True, help="作成するプレイヤーの名前")
    args = parser.parse_args()
    
    db = DBManager()
    print(f"データベースに接続中...")
    player_data = db.get_or_create_player(args.player_name)
    name = player_data[1]
    print(f"プレイヤ：{name} を作成しました。")

if __name__ == "__main__":
    main()