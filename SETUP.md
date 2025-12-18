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

## 2. Python仮想環境の準備

授業等で指定された `rsl_base` 環境を使用します。

```bash
# 1. 仮想環境の有効化
source ~/venv/rsl_base/bin/activate

# 2. 依存パッケージのインストール (初回のみ)
pip install -r requirements.txt
```

## 3. データベースの準備

付属のPythonスクリプトを使用して、データベースを自動構築します。

```bash
# データベースセットアップスクリプトの実行
python3 setup_db.py
```

※ 実行中にパスワードを求められた場合は、Linuxのログインパスワードを入力してください。
※ `✅ データベースのセットアップが完了しました！` と表示されれば成功です。

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
PGPASSWORD=ryukoku psql -h localhost -U dbprog01 -d testraiddb
```

## 5. 最新のコードを取得する場合 (git pull)

他のメンバーがコードを更新した場合、以下のコマンドで自分の環境に取り込むことができます。

```bash
# 1. リポジトリのディレクトリに移動
cd ~/dbprog/dbkadai

# 2. 最新の変更を取得
git pull

# 3. 必要であれば依存パッケージを更新
pip install -r requirements.txt

# 4. データベース構造に変更がある場合は再セットアップ（データは消えます）
# python3 setup_db.py
```
