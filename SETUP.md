# 開発環境構築ガイド (チームメンバー向け)

このリポジトリには、RPG演習プロジェクトのソースコード一式が含まれています。
以下の手順に従って、Linux Mate環境で開発環境を構築してください。

## 1. ソースコードの取得

作業用ディレクトリ（例: `~/dbprog/`）を作成し、そこにリポジトリをクローンします。

```bash
# 作業用ディレクトリの作成と移動
mkdir -p ~/dbprog
cd ~/dbprog

# gitがインストールされていない場合はインストール
sudo apt update
sudo apt install -y git

# リポジトリのクローン
git clone https://github.com/hiroyuki-rdx/dbkadai.git
cd dbkadai

# VS Codeで開く場合
code .
```

## 2. データベースの準備

PostgreSQLを使用してデータベースを構築します。

1.  PostgreSQLにログインします。
    （パスワードを求められたら `ryukoku` と入力してください）

    ```bash
    sudo -u postgres psql
    ```

2.  `postgres=#` というプロンプトが表示されたら、以下のSQLを**そのままコピー＆ペースト**して実行してください。
    （これにより、古いデータがあれば消去され、新しい `testraiddb` が作成されます）

    ```sql
    -- データベース 'testraiddb' があれば削除してリセット（ユーザーは削除しません）
    DROP DATABASE IF EXISTS testraiddb;

    -- ユーザー 'dbprog' を作成
    -- ※「role "dbprog" already exists」というエラーが出ても無視して構いません
    CREATE USER dbprog WITH PASSWORD 'ryukoku';
    
    -- 念のためパスワードを確実に設定
    ALTER USER dbprog WITH PASSWORD 'ryukoku';

    -- データベース 'testraiddb' を作成（所有者を dbprog に設定）
    CREATE DATABASE testraiddb OWNER dbprog;

    -- 念のため権限を付与
    GRANT ALL PRIVILEGES ON DATABASE testraiddb TO dbprog;
    ```

3.  エラーが出なければ、`\q` と入力して `psql` を終了します。

    ```sql
    \q
    ```

## 3. Python仮想環境の準備

### A. 既存の環境 (rsl_base) を使用する場合

授業等で指定された `rsl_base` 環境がある場合は、それを使用できます。

```bash
# 1. 仮想環境の有効化
source ~/venv/rsl_base/bin/activate

# 2. 依存パッケージのインストール (初回のみ)
pip install -r requirements.txt
```

### B. 新しく環境を作成する場合

個別に環境を作成したい場合は、以下の手順で行います。

```bash
# 1. 仮想環境 (.venv) の作成
python3 -m venv .venv

# 2. 仮想環境の有効化
source .venv/bin/activate

# 3. 依存パッケージのインストール
pip install -r requirements.txt
```

## 4. ゲームの実行

準備が整いました。以下のコマンドでゲームを開始してください。

```bash
python3 main.py
```

プログラムが自動的に `testraiddb` に接続し、必要なテーブルを作成してゲームを開始します。

---

### 補足: データベースの中身を確認したい場合

ゲームのデータを確認したいときは、以下のコマンドで接続できます。

```bash
PGPASSWORD=ryukoku psql -h localhost -U dbprog -d testraiddb
```
