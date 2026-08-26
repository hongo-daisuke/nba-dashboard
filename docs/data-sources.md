# データソース選定の記録

このドキュメントは参照用。日常的な禁止事項は CLAUDE.md 本体に記載済み。
ここには**なぜそうなったか**の経緯と実測値のみを残す。

## 経緯：なぜこのデータソースなのか

### 1. nba_api（stats.nba.com 系）— 不採用

`stats.nba.com` は AWS / GCP / Azure の IP をブロックする。

**最も危険な点：403 ではなくタイムアウト/ハングする。**
ローカル開発環境では完全に動作するため、テストをすり抜けてデプロイ後に初めて失敗する。
「ローカルで動いた」は Lambda で動く証拠にならない。

### 2. cdn.nba.com（nba_api の live 系）— 不採用

Akamai の防御下。当初は「保護されていないので使える」と想定したが、実測で否定された。

- 家庭用IP（自宅 MacBook）から 403
- AWS（ap-northeast-1 / CloudShell）からも 403
- User-Agent を変更しても改善せず
- `errors.edgesuite.net` へのリダイレクト = Akamai
- TLS フィンガープリント（JA3）による判定と推測される
- **接続元IPに依存しないため、実行環境を変えても解決しない**

`curl_cffi` 等で TLS 指紋を偽装すれば通る可能性はあるが、
**相手のボット対策をかいくぐる設計は採用しない。** ルール変更のたびに壊れるため。

### 3. balldontlie.io — 不採用（予備として保持）

サードパーティの NBA データ API。課金ティアで取得できるデータが変わる。

| ティア | 月額 | レート | 取得可能 |
|---|---|---|---|
| Free | $0 | 5 req/min | Teams, Players, Games のみ |
| ALL-STAR | $9.99 | 60 req/min | + 試合ごとの選手スタッツ, 故障者情報 |
| GOAT | $39.99 | 600 req/min | + シーズン平均, 順位表, ボックススコア, 各種アドバンスト |

予算が $0 のため Free では要件（シーズン平均・順位表・ボックススコア）を満たせず不採用。
ただし ESPN が死んだ場合の代替として、アダプタを追加すれば移行できる状態を保つ。

### 4. ESPN 公開JSON — **採用**

`site.api.espn.com` / `site.web.api.espn.com`。認証不要。

ローカル・AWS 双方から 200 を確認済み。過去日付の scoreboard も取得可能なため、
バックフィルによって過去シーズンのデータも構築できる。

---

## 実測結果（意見ではなく計測値）

| 対象 | 自宅IP | AWS (ap-northeast-1 / CloudShell) |
|---|---|---|
| `stats.nba.com/stats/*` | 未計測 | **ブロック**（本プロジェクトで実際に遭遇した事象） |
| `cdn.nba.com/.../liveData/scoreboard/todaysScoreboard_00.json` | **403** | **403** |
| `cdn.nba.com/.../liveData/boxscore/boxscore_0022000181.json` | **403** | **403** |
| `site.api.espn.com/.../nba/teams` | 200 | **200** |
| `site.api.espn.com/.../nba/scoreboard?dates=20260118` | 200 | **200** |
| `site.api.espn.com/.../nba/summary?event={id}` | 200 | **200** |
| `site.api.espn.com (v2)/.../nba/standings` | 200 | **200** |

cdn.nba.com は自宅の家庭用IP・AWS の双方から 403。User-Agent 変更でも改善しない。
IPレンジ依存ではないため、プロキシや別リージョンからの再試行でも解決しない見込み。
**このエンドポイントの再検討は不要。**

### summary エンドポイントのデータ構造（実測）

```
boxscore.players[]                         # チームごと（2要素）
  .team.abbreviation                       # チーム略称
  .statistics[0]
    .keys[]     → ['minutes', 'points', 'fieldGoalsMade-fieldGoalsAttempted',
                    'threePointFieldGoalsMade-threePointFieldGoalsAttempted',
                    'freeThrowsMade-freeThrowsAttempted', 'rebounds', 'assists',
                    'turnovers', 'steals', 'blocks', 'offensiveRebounds',
                    'defensiveRebounds', 'fouls', 'plusMinus']
    .athletes[]
      .athlete.displayName                 # 選手名
      .stats[]    → ['36', '16', '7-20', '1-4', '1-1', '8', '9', '4', '0', '0', '2', '6', '0', '-7']
```

**パース上の注意点（実装必須）：**
- `'7-20'` 形式の複合文字列は `fg_made=7, fg_attempted=20` に分解して正規化して保存する。文字列のまま保存すると FG% 等の再計算ができない
- DNP・欠場選手は `stats` が空配列または `'--'` になる。zip 前にガードが必要
- `statistics[0]` の固定参照や keys のインデックス固定参照は禁止。`keys` 配列から名前で引く（ESPN 側が列を追加したら壊れるため）

---

## 要件（アクセスパターン）

1. 全チーム一覧
2. チーム詳細 ＋ 所属選手
3. 指定日の試合一覧
4. 試合詳細（ボックススコア）
5. 選手詳細 ＋ シーズン平均スタッツ
6. カンファレンス順位表

---

## データモデル（DynamoDB 6テーブル構成）

シングルテーブル設計はデバッグコスト対パフォーマンスのトレードオフを検討した結果、採用しない。
アクセスパターン1〜6のそれぞれに対して明示的なテーブル/GSIを対応させる。

| テーブル | PK | SK | GSI | 対象パターン |
|---|---|---|---|---|
| TeamsTable | `team_id` | - | `conference-index` (PK=conference, SK=team_id) | 1, 2 |
| PlayersTable | `player_id` | - | `team-index` (PK=team_id, SK=player_id)<br>`position-index` (PK=position, SK=player_id) | 2, 5 |
| PlayerStatsTable | `player_id` | `season` | - | 5（シーズン集計） |
| GamesTable | `game_date` | `game_id` | `home-team-index` (PK=home_team_id, SK=game_date)<br>`away-team-index` (PK=away_team_id, SK=game_date)<br>`game-id-index` (PK=game_id) | 3, 4 |
| **GameStatsTable** | `game_id` | `player_id` | `player-index` (PK=player_id, SK=game_date) | 4（ボックススコア生データ） |
| **StandingsTable** | `season` | `conference#seed` | - | 6 |

※ **太字**は既存スキーマに存在しない追加テーブル。`game-id-index` も GamesTable への追加。

### アクセスパターンとの対応

| パターン | 操作 |
|---|---|
| 1. 全チーム一覧 | TeamsTable `conference-index` を East/West で 2 回 Query（Scan 不要） |
| 2. チーム詳細+所属選手 | TeamsTable PK=team_id + PlayersTable `team-index` |
| 3. 指定日の試合一覧 | GamesTable PK=game_date |
| 4. 試合詳細（ボックススコア） | GamesTable `game-id-index` で試合情報 + GameStatsTable PK=game_id で全選手スタッツ |
| 5. 選手詳細+シーズン平均 | PlayersTable PK=player_id + PlayerStatsTable PK=player_id |
| 6. カンファレンス順位表 | StandingsTable PK=season, SK begins_with "East#" or "West#" |

### 既知のトレードオフ

- `home-team-index` / `away-team-index` の分離：「あるチームの全試合」は 2 クエリ+マージが必要。
  単一 GSI に統合するにはゲームごとに 2 アイテム書く等の設計変更が必要なため、現状維持。
  マージはリポジトリ層で吸収する。
- `StandingsTable` の SK は `East#01`（ゼロパディング）とする。DynamoDB の辞書順ソートで順位が正しく並ぶ。

### 設計上の必須要件

- **生データと集計結果を両方保持する。** 集計結果だけを保存する設計にしないこと。
  後から新しい指標（eFG% 等）を追加したくなった際に再計算できなくなる
- 集計は日次バッチで実行し、結果を書き戻す。配信側で計算しない
- 収集（バッチ）と配信（API）を分離する。配信 Lambda は DynamoDB のみを読み、
  外部APIを一切叩かない

---

## 未検証事項

**以下は未確認。確定事項として実装しないこと。実装前に実際に叩いてレスポンス構造を確認する。**

- 選手のシーズン集計が ESPN から直接取得できるか
  - 取得できない場合はボックススコア（GameStatsTable）を積み上げて自前集計する（実現可能）
- 過去シーズンの scoreboard が何年まで遡れるか（バックフィルの範囲確定に必要）

いずれも「取得できなければ自前計算」でリカバリ可能なため、ブロッカーではない。

### 確認済み（未検証から移動）

- `summary?event={id}` のボックススコアの構造 → **確認済み**（上記「実測結果」参照）
- `standings` エンドポイントの可用性 → **確認済み**（East/West・W-L・playoffSeed 等を取得できる）

---

## 環境

- フロントエンド: Vue 3 + TypeScript
- バックエンド: Python (AWS Lambda) + SAM
- データストア: DynamoDB
- リージョン: ap-northeast-1
- スケジューラ: EventBridge
- 日付基準: **ET（米国東部時間）**。JST で日次バッチを組むと試合を取りこぼす
- APIキーが必要になった場合は SSM Parameter Store（SecureString）に保存。コードに直書きしない
