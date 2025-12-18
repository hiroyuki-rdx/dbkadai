import subprocess
import sys

def run_setup():
    print("🚀 データベースのセットアップを開始します...")
    print("※ sudoパスワードを求められた場合は、Linuxのログインパスワードを入力してください。")

    # 実行するSQLコマンド
    # 注意: CREATE DATABASE はトランザクションブロック内で実行できないため、
    # psqlに渡して順次実行させます。
    sql_commands = """
    -- 既存のDBがあれば削除
    DROP DATABASE IF EXISTS testraiddb;

    -- ユーザー作成 (存在する場合はエラーになるが無視して続行させるためにDOブロックは使わず、
    -- エラーが出ても後続のALTERでパスワードを設定する方針をとる)
    -- ただし、psqlで単純に流すとエラーで止まる設定でなければ続行する。
    """

    # ユーザー作成とDB作成を分けます
    
    # 1. ユーザー作成 (失敗してもOKなように)
    user_sql = """
    DO
    $do$
    BEGIN
       IF NOT EXISTS (
          SELECT FROM pg_catalog.pg_roles
          WHERE  rolname = 'dbprog') THEN
          CREATE ROLE dbprog LOGIN PASSWORD 'ryukoku';
       ELSE
          ALTER ROLE dbprog WITH PASSWORD 'ryukoku';
       END IF;
    END
    $do$;
    """

    # 2. DB作成
    db_sql = """
    CREATE DATABASE testraiddb OWNER dbprog;
    GRANT ALL PRIVILEGES ON DATABASE testraiddb TO dbprog;
    """

    try:
        # ユーザー作成・設定
        print("\n--- ユーザー設定 (dbprog) ---")
        run_psql(user_sql)

        # DB作成
        print("\n--- データベース作成 (testraiddb) ---")
        run_psql(db_sql)

        print("\n✅ データベースのセットアップが完了しました！")
        print("   User: dbprog")
        print("   Pass: ryukoku")
        print("   DB  : testraiddb")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

def run_psql(sql):
    cmd = ['sudo', '-u', 'postgres', 'psql', '-v', 'ON_ERROR_STOP=1']
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=sql)
    
    if process.returncode != 0:
        print("エラー出力:")
        print(stderr)
        raise Exception("SQL実行に失敗しました")
    
    if stdout.strip():
        print(stdout)

if __name__ == "__main__":
    run_setup()
