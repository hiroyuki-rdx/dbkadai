import sys
from db_manager import DBManager

def safe_input(prompt):
    """
    ユーザー入力を受け取り、'exit' が入力された場合はプログラムを終了する。
    それ以外の場合は入力値を返す。
    """
    try:
        val = input(prompt)
    except EOFError:
        # Ctrl+D などの場合も終了扱いにする
        print("\nゲームを終了します。")
        _reset_and_exit()

    if val.strip().lower() == "exit":
        print("ゲームを終了します。")
        _reset_and_exit()
    return val

def _reset_and_exit():
    """データを初期化して終了する"""
    print("🔄 ゲームデータを初期化中...")
    try:
        db = DBManager()
        db.reset_all_game_data()
        print("✅ 初期化完了")
    except Exception as e:
        print(f"⚠️ 初期化中にエラーが発生しました: {e}")
    sys.exit(0)
