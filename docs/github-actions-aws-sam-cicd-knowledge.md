# GitHub Actions + AWS SAM CI/CD 設計・構築ナレッジ

> 対象: Vue/Vite フロントエンド + AWS SAM バックエンドを 1 リポジトリで管理し、GitHub Actions から dev / prd へ安全にデプロイする構成  
> 初版: 2026-08-20 / 更新: 2026-08-26  
> ベース: 個人学習用 `nba-dashboard` の現在実装と、構築時のトラブルシュート記録

---

## 0. この資料の目的

この資料は「完成した YAML の説明書」ではなく、**なぜその構成にしたのか、何が問題になり、どう切り分け、最終的にどうすれば再利用できる形になるのか**を残すためのナレッジです。

特に次の観点を重視します。

- GitHub Actions で何ができるのか
- どこに何を設定するのか
- なぜその設定が必要なのか
- 似た構成の別案と何が違うのか
- 実際に遭遇したエラーをどう切り分けたのか
- 別プロジェクトへ横展開するとき、どこを置き換えればよいのか

アプリケーション機能そのものではなく、CI/CD・Repository 運用・AWS 認証・デプロイ設計に集中します。

### この資料の前提

現在のリポジトリ構成を基準に、Workflow、SAM Template、`samconfig.toml`、Frontend 設定、Git 履歴を確認しています。

CI/CD の基本構成を整えた後もアプリケーション開発は進み、SAM Template には DynamoDB、NBA データ取得 Batch Lambda、ScheduleV2 などが追加されていますが、`.github/workflows/` の基本構成は維持されています。

初期 Frontend Deploy の説明は、現在確認できる初期 Workflow と、その後に採用した設計判断をもとに整理しています。

> **表記ルール: 今回の実装 / 実測**  
> `nba-dashboard` の実ファイルと、構築・検証時の記録で確認した内容です。
>
> **表記ルール: 一般仕様**  
> GitHub / AWS / Vite の公式仕様として確認した内容です。今回の実測結果と一般仕様が混ざらないように分けて記載します。

### 0.1 5分で分かる全体像

#### Architecture

```text
Browser
   |
   +----------------------> CloudFront -> Private S3
   |
   +----------------------> API Gateway
                               |
                               v
                         API Lambda (Python)
                               |
                               v
                            DynamoDB

ScheduleV2
   |
   v
Batch Lambda (Python)
   |
   v
DynamoDB
```

Infrastructure は AWS SAM / CloudFormation で管理します。現在の SAM Template では、Frontend 配信用の S3 / CloudFront、API Gateway / API Lambda に加え、DynamoDB と NBA データ取得 Batch Lambda / ScheduleV2 も管理しています。

#### PR → dev / main → Deploy

```text
feature/*
   |
   +--> Pull Request
          |
          +--> Backend Check
          +--> Frontend Check
          |
          v
        Merge
          |
          +--> dev  -> dev Environment
          |
          +--> main -> prd Environment
```

`feature/*` は共有環境へ直接 Deploy せず、PR Check を通して `dev` / `main` へ Merge された後に Deploy します。

#### Backend → Frontend

```text
deploy.yml
   |
   v
deploy-backend.yml
   |  SAM Deploy
   |  CloudFormation Outputs
   |  - ApiEndpoint
   |  - FrontendBucketName
   |  - CloudFrontDistributionId
   v
deploy-frontend.yml
   |  .env 生成
   |  Vite Build
   |  S3 root Deploy
   v
CloudFront Invalidation
```

Frontend は Backend / Infrastructure が作った値に依存するため、`needs: backend` で順序を保証します。

#### GitHub Actions → AWS OIDC

```text
GitHub Actions
   |
   | OIDC token
   v
AWS STS
   |
   | AssumeRoleWithWebIdentity
   v
IAM Role
   |
   v
Temporary Credentials
```

固定 Access Key / Secret Access Key を GitHub に保存せず、一時 Credential で AWS へ Deploy します。

ここまでで全体像は十分です。以降は、**「なぜこの構成になったか」「設定方法」「実際にハマった問題」**を必要に応じて読んでください。

### 0.2 読む順番

| 読みたい内容 | 推奨する章 |
|---|---|
| まず全体像だけ知りたい | 0.1 → 1 |
| 初めて構成を理解する | 1 → 3 → 4 → 5 → 6 → 8 → 10 → 25 |
| 実際に設定・横展開する | 20 → 21 → 25 |
| Secret / OIDC 周りを理解する | 8 → 9 → 10 → 11 |
| エラーを調べる | 22 → 該当する詳細章 |
| この構成に至った経緯を知る | 3 → 23 |

---

# 1. 最終構成の要点

5分版の全体像は「0.1 5分で分かる全体像」を参照してください。ここでは、以降の詳細章を読むために Branch と Deploy の対応だけを押さえます。

```text
Pull Request Check -> merge -> Deploy -> Backend / SAM -> CloudFormation Outputs -> Frontend
```

| Branch | Pull Request Check | Deploy | GitHub Environment | SAM config-env |
|---|---:|---:|---|---|
| `feature/*` | Yes | No | - | - |
| `dev` | Yes | Yes | `dev` | `dev` |
| `main` | Yes | Yes | `prd` | `prd` |

**feature branch を共有 dev 環境へ直接デプロイしない**のが今回の方針です。複数 feature branch が同じ共有環境を上書きすると、PR で確認したコードと実際の dev 環境が一致しなくなるためです。

AWS/SAM の現在の基本命名は次です。

```text
ResourcePrefix = hongo
Environment    = dev / prd
ProjectName    = nba-dashboard

dev Stack = hongo-dev-nba-dashboard
prd Stack = hongo-prd-nba-dashboard
```

詳細は、Workflow 構成を 4 章、Backend → Frontend の順序を 5 章、値の受け渡しを 6 章で説明します。

---

# 2. モノレポとポリレポ: 今回どちらを選んだか

## 2.1 モノレポとは

モノレポでは、Frontend と Backend を同じ Git Repository に置きます。

今回の構成はこれです。

```text
nba-dashboard/
├── frontend/
├── backend/
└── .github/
    └── workflows/
        ├── backend-pr-check.yml
        ├── frontend-pr-check.yml
        ├── deploy.yml
        ├── deploy-backend.yml
        └── deploy-frontend.yml
```

## 2.2 ポリレポ（マルチレポ）とは

Frontend / Backend を別 Repository に分けます。

```text
nba-dashboard-frontend/
├── frontend source
└── .github/workflows/

nba-dashboard-backend/
├── SAM source
└── .github/workflows/
```

## 2.3 今回モノレポを選んだ理由

今回のシステムでは Frontend と Backend のデプロイ依存が強いため、モノレポが扱いやすい構成でした。

Backend の SAM Deploy 後に初めて、次の値が確定します。

- API Gateway Endpoint
- Frontend S3 Bucket 名
- CloudFront Distribution ID

Frontend はその値を使って Build / Deploy します。

同じ Repository なら、GitHub Actions の `needs` と reusable workflow outputs を使って次のように直結できます。

```yaml
jobs:
  backend:
    uses: ./.github/workflows/deploy-backend.yml

  frontend:
    needs:
      - backend

    uses: ./.github/workflows/deploy-frontend.yml

    with:
      api_endpoint: ${{ needs.backend.outputs.api_endpoint }}
```

このため、今回の要件では「Backend と Frontend を別 Repository に分けるメリット」よりも「同一 Run 内で順番と値の受け渡しを管理できるメリット」の方が大きいと判断しました。

## 2.4 比較

| 観点 | モノレポ | ポリレポ |
|---|---|---|
| Frontend / Backend | 同一 Repo | 別 Repo |
| 1 PR で両方変更 | 容易 | Repo をまたぐため難しい |
| Backend → Frontend の順序 | `needs` で表現可能 | Repo 間連携が必要 |
| CloudFormation Outputs 受け渡し | Workflow output で直接 | SSM 等の共有ストアが必要になりやすい |
| Branch 戦略 | 共通化しやすい | Repo ごとに独立 |
| Rulesets | 1 Repo で設定 | 各 Repo で設定 |
| チームの独立性 | 中 | 高 |
| Release 周期の独立性 | 中 | 高 |
| CI/CD の初期複雑度 | 低め | 高め |

## 2.5 ポリレポにするなら何が変わるか

Repository を分けると、次は使えません。

```yaml
needs:
  - backend
```

`needs` は同じ Workflow 内の Job 依存を表すため、別 Repository の Workflow には直接つなげられません。

そこで、Backend の成果物を AWS 側へ保存する方式が分かりやすいです。

```text
Backend Repository
    |
    +--> sam deploy
    |
    +--> CloudFormation Outputs
    |
    +--> SSM Parameter Store
          - /nba-dashboard/dev/api-endpoint
          - /nba-dashboard/dev/frontend-bucket
          - /nba-dashboard/dev/cloudfront-distribution-id

Frontend Repository
    |
    +--> AWS OIDC
    |
    +--> SSM Parameter Store から取得
    |
    +--> .env 生成
    |
    +--> Build / S3 / CloudFront
```

Backend 側のイメージ:

```yaml
- name: Store deployment outputs
  run: |
    aws ssm put-parameter \
      --name "/nba-dashboard/${TARGET_ENVIRONMENT}/api-endpoint" \
      --type String \
      --overwrite \
      --value "$API_ENDPOINT"
```

Frontend 側のイメージ:

```yaml
- name: Resolve backend endpoint
  run: |
    API_ENDPOINT="$(
      aws ssm get-parameter \
        --name "/nba-dashboard/${TARGET_ENVIRONMENT}/api-endpoint" \
        --query 'Parameter.Value' \
        --output text
    )"
```

また、Backend Deploy 完了後に Frontend Workflow を API で起動する構成も可能ですが、認証・再実行・失敗時の再開位置・Repository 間権限などを別途設計する必要があります。

### ポリレポを選びやすいケース

- Frontend / Backend が別チーム
- Release 周期を完全に独立させたい
- Backend を複数 Frontend から利用する
- Repository 単位で IAM / GitHub 権限を厳密に分けたい
- 1 つの Backend が複数製品から使われる

今回のように 1 アプリケーションとして同時に dev/prd へ出すなら、モノレポはかなり自然です。

---

# 3. 初期構成: Frontend と Backend が別々にデプロイを開始していた

初期 Git 履歴には、次の独立 Workflow がありました。

```text
.github/
├── build-and-sync-to-s3-learning.yml
└── build-and-deploy-backend-learning.yml
```

初期 Frontend Workflow は概ね次の責務を 1 Job に持っていました。

```text
Frontend change
   |
   +--> npm ci
   +--> Unit Test
   +--> ENV_FILE -> .env
   +--> BUILD_MODE を GitHub Variable から取得
   +--> Vite Build
   +--> AWS OIDC
   +--> S3 sync
   +--> CloudFront Invalidation
```

設定値として、当初は次のようなものを GitHub Environment に持たせる想定でした。

```text
AWS_ROLE_ARN
AWS_REGION
AWS_ACCOUNT_ID
ENV_FILE
BUILD_MODE
S3_BUCKET_NAME
```

Backend は別 Workflow で独立して SAM Deploy していました。

## 問題1: Frontend と Backend の実行順序を保証できない

独立した `push` Workflow にすると、Frontend と Backend が同時に走れます。

```text
push
├--> backend workflow
└--> frontend workflow
```

しかし Frontend は、Backend が作る API Gateway URL を必要とします。

```text
Frontend Build
    |
    +--> API URL が必要
              ^
              |
          SAM Deploy 後に確定
```

このため、**Backend を先に完了させ、その結果を Frontend に渡す必要がある**と整理しました。

## 問題2: 同じ情報を複数箇所で手入力する

S3 Bucket、Stack Name、Build Mode、API URL を GitHub Variables へ持つと、AWS / `samconfig.toml` / GitHub の間で同じ情報を重複管理します。

```text
CloudFormation
GitHub Environment
samconfig.toml
```

この状態では、どれが正しい値なのか分かりづらくなります。

そこで最終的には Source of Truth を明確にしました。

| 値 | Source of Truth |
|---|---|
| Stack Name | `samconfig.toml` |
| API Endpoint | CloudFormation Output |
| Frontend S3 Bucket | CloudFormation Output |
| CloudFront Distribution ID | CloudFormation Output |
| dev / prd | Orchestrator の `target_environment` |
| AWS Region | GitHub Environment Variable |
| AWS Account ID | GitHub Environment Variable |

---

# 4. 最終 Workflow 構成: Orchestrator + Reusable Workflows

最終的に Deploy を 3 ファイルへ分離しました。

```text
.github/workflows/
├── deploy.yml
├── deploy-backend.yml
└── deploy-frontend.yml
```

## 4.1 `deploy.yml`: 唯一の入口

このファイルだけが `push` / `workflow_dispatch` を持ちます。

主な責務:

- Deploy の開始条件
- Branch → Environment の決定
- feature branch を拒否
- Deploy 全体の concurrency
- Backend → Frontend 順序保証
- Backend Outputs → Frontend Inputs の受け渡し

```yaml
on:
  push:
    branches:
      - main
      - dev
    paths:
      - 'backend/**'
      - 'frontend/**'
      - '.github/workflows/deploy.yml'
      - '.github/workflows/deploy-backend.yml'
      - '.github/workflows/deploy-frontend.yml'
```

README だけの変更などでは Deploy しません。

## 4.2 `deploy-backend.yml`: Backend の責務だけを持つ

`workflow_call` だけを持つ reusable workflow です。

```yaml
on:
  workflow_call:
    inputs:
      target_environment:
        required: true
        type: string

    outputs:
      api_endpoint:
        value: ${{ jobs.build-and-deploy.outputs.api_endpoint }}
      frontend_bucket_name:
        value: ${{ jobs.build-and-deploy.outputs.frontend_bucket_name }}
      cloudfront_distribution_id:
        value: ${{ jobs.build-and-deploy.outputs.cloudfront_distribution_id }}
```

この Workflow 自身は branch を見て dev/prd を決めません。決定済みの `target_environment` を受け取るだけです。

## 4.3 `deploy-frontend.yml`: Frontend の責務だけを持つ

Backend が返した値を input として受け取ります。

```yaml
on:
  workflow_call:
    inputs:
      target_environment:
        required: true
        type: string
      api_endpoint:
        required: true
        type: string
      frontend_bucket_name:
        required: true
        type: string
      cloudfront_distribution_id:
        required: true
        type: string
```

## 4.4 なぜ 1 つの巨大 YAML にしなかったか

1 ファイルでも実装できますが、Frontend と Backend の責務が混ざります。

```text
巨大 deploy.yml
├── Branch 判定
├── Python / SAM
├── CloudFormation
├── Node / Vitest
├── .env
├── S3
└── CloudFront
```

Reusable Workflow に分けることで、入口と実処理の責務が分離されます。

```text
deploy.yml
   |
   +--> deploy-backend.yml
   |
   +--> deploy-frontend.yml
```

「実行条件を変える」変更と「Backend のデプロイ方法を変える」変更が別ファイルになるため、レビューもしやすくなります。

---

# 5. Backend → Frontend の順序を保証する

最終構成の中核です。

```yaml
frontend:
  needs:
    - prepare
    - backend
```

`needs: backend` により、Backend が成功するまで Frontend は開始しません。

```text
prepare
   |
   v
backend
   |
   | success
   v
frontend
```

Backend が失敗すれば Frontend はスキップされます。実際のトラブルシュートでも、Backend の OIDC / SAM Deploy が失敗したとき Frontend が開始されなかったため、順序制御が正しく機能していることを確認できました。

## Frontend だけ変わったときも Backend を通す理由

現在の Trigger は `backend/**` または `frontend/**` の変更で Deploy 全体を開始します。

そのため Frontend-only change でも Backend Workflow を通ります。

ただし SAM Deploy は次を付けています。

```bash
--no-fail-on-empty-changeset
```

CloudFormation に変更がなければ正常終了し、そのまま Frontend へ進みます。

これは job-level の複雑な path 判定を入れず、**常に同じデプロイ経路を通す単純さを優先した設計**です。

将来デプロイ時間が問題になったら、変更ファイルを判定して Backend をスキップする最適化を追加できます。ただし、その場合は「Backend outputs をどこから取得するか」という別問題が増えます。

---

# 6. CloudFormation Outputs を契約にする

SAM Template は、Frontend Workflow が必要な値を Outputs として公開します。

```yaml
Outputs:
  ApiEndpoint:
    Value: !Sub 'https://${FrontendApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}'

  FrontendBucketName:
    Value: !Ref FrontendBucket

  CloudFrontDistributionId:
    Value: !Ref FrontendDistribution
```

Backend Workflow は Deploy 後に `aws cloudformation describe-stacks` で値を取得します。

```text
SAM Deploy
   |
   v
CloudFormation Stack
   |
   +--> ApiEndpoint
   +--> FrontendBucketName
   +--> CloudFrontDistributionId
   |
   v
Workflow Outputs
   |
   v
Frontend Inputs
```

この設計により、次の GitHub Variables は不要になりました。

```text
S3_BUCKET_NAME   -> 不要
STACK_NAME       -> 不要
BUILD_MODE       -> 不要
API Gateway URL  -> 不要
```

### なぜ手入力を減らすのか

手入力値が増えると、Infrastructure を作り直したときに GitHub 側だけ古い値になる事故が起こります。

```text
AWS: new bucket
GitHub: old bucket  <-- drift
```

CloudFormation が作った値は CloudFormation から取得することで、この drift を減らせます。

---

# 7. API Endpoint の bootstrap 問題

これは今回の設計で重要だった問題です。

Frontend の Vite Build は API URL を必要とします。しかし、初回 Deploy では API Gateway 自体がまだありません。

```text
API URL がない
    |
    +--> Frontend Build できない

でも

SAM Deploy しない
    |
    +--> API URL が作られない
```

> **今回の実装 / 実測**  
> `ENV_FILE` には API Gateway の実 URL を固定で保存せず、`VITE_API_BASE_URL=__API_ENDPOINT__` のようにプレースホルダーを持たせています。`deploy-backend.yml` が CloudFormation Output `ApiEndpoint` を取得し、`deploy.yml` がそれを `deploy-frontend.yml` へ input として渡します。

```dotenv
VITE_API_BASE_URL=__API_ENDPOINT__
VITE_APP_TITLE=Example
```

Frontend Workflow では、Build 直前にプレースホルダーを置換して一時的な `.env` を生成します。

```bash
PLACEHOLDER="__API_ENDPOINT__"
RENDERED_ENV="${ENV_FILE//$PLACEHOLDER/$API_ENDPOINT}"
printf '%s\n' "$RENDERED_ENV" > .env
```

```text
SAM Deploy
   |
   v
ApiEndpoint Output
   |
   v
ENV_FILE の __API_ENDPOINT__ を置換
   |
   v
frontend/.env を一時生成
   |
   v
Vite Build
   |
   v
.env 削除
```

これにより、**AWS が空の状態からでも 1 回の Deploy Workflow で Backend と Frontend を構築できる**ようになります。

> **一般仕様: Vite の環境変数**  
> `VITE_*` が付いた値は Build 時にクライアント側コードへ埋め込まれます。したがって、`ENV_FILE` を GitHub Secret に保存していても、`VITE_*` の値そのものをブラウザから秘匿できるわけではありません。API Endpoint や画面タイトルのような公開してよい値に限定し、API Key、Password、Secret Key などの機密情報は `VITE_*` に入れません。

GitHub Secret として `ENV_FILE` を保持する目的は、GitHub 上で設定値を不用意に表示・編集・ログ出力しない運用に寄せるためであり、**Frontend の秘密情報を安全に配信する仕組みではありません**。

> **今回の Repository で紛らわしい点**  
> `frontend/.env`、`.env.dev`、`.env.prd` などのローカル用ファイルも存在しますが、root `.gitignore` の `.env` / `.env.*` で Git 管理対象外になっています。GitHub Actions の Deploy で使う Source of Truth はこれらのローカルファイルではなく、GitHub Environment の `ENV_FILE` と CloudFormation Output `ApiEndpoint` です。

---

# 8. GitHub Environment: dev / prd の設定

Environment は Repository の次の場所で作成します。

```text
Settings
  -> Environments
      -> dev
      -> prd
```

最終的に使う値は 4 つです。

## Environment Secrets

```text
AWS_ROLE_ARN
ENV_FILE
```

## Environment Variables

```text
AWS_REGION
AWS_ACCOUNT_ID
```

例:

```text
Environment: dev
├── Secrets
│   ├── AWS_ROLE_ARN
│   └── ENV_FILE
└── Variables
    ├── AWS_REGION
    └── AWS_ACCOUNT_ID
```

`prd` も同じキー名で値だけ切り替えます。

### Secret と Variable の考え方

- `secrets.X`: GitHub 上で Secret として扱い、ログへの露出を抑えたい設定
- `vars.X`: 環境別に切り替える非機密設定

> **今回の実装 / 実測**  
> `AWS_ROLE_ARN` と `ENV_FILE` は Environment Secret、`AWS_REGION` と `AWS_ACCOUNT_ID` は Environment Variable として管理しています。Role ARN 自体は Credential ではありませんが、現在の Environment 設計に合わせて Secret 側へ置いています。

> **一般仕様 / 注意**  
> GitHub Secret に置いた値が、そのままアプリケーション上でも秘密になるわけではありません。特に Vite の `VITE_*` はクライアント Bundle へ含まれるため、`ENV_FILE` 内には公開してよい Frontend 設定だけを入れます。

## Deployment branch の推奨

Deploy Workflow 自体が branch を制限していますが、Environment 側でも二重に制限すると安全です。

```text
dev -> dev branch
prd -> main branch
```

`feature/*` は最終設計では Deploy しないため、dev Environment の deployment branches に残さない方が意図が明確です。

---

# 9. Reusable Workflow で Secrets が空になった問題

今回かなり時間を使ったポイントです。この章は、**今回観測した事実**と**GitHub の一般仕様**を分けて読みます。

> **今回の実測**  
> Backend Workflow の validation で `AWS_REGION` / `AWS_ACCOUNT_ID` は取得できる一方、`AWS_ROLE_ARN` が空になる状態を確認しました。その後、caller の reusable workflow call Job に `secrets: inherit` を追加した構成で問題が解消しました。

```text
AWS_ROLE_ARN: 空
AWS_REGION: ap-northeast-1
AWS_ACCOUNT_ID: 値あり
```

## 9.1 Environment Secret 自体が壊れているのか確認

一時的に通常 Job を `deploy.yml` へ追加し、Secret の**値ではなく存在有無だけ**を確認しました。

```yaml
debug-environment:
  runs-on: ubuntu-latest

  environment:
    name: ${{ needs.prepare.outputs.target_environment }}

  steps:
    - name: Check environment values
      env:
        AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
        ENV_FILE: ${{ secrets.ENV_FILE }}
        AWS_REGION: ${{ vars.AWS_REGION }}
        AWS_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}
      run: |
        echo "AWS_REGION exists: $([[ -n \"${AWS_REGION:-}\" ]] && echo yes || echo no)"
        echo "AWS_ACCOUNT_ID exists: $([[ -n \"${AWS_ACCOUNT_ID:-}\" ]] && echo yes || echo no)"
        echo "AWS_ROLE_ARN exists: $([[ -n \"${AWS_ROLE_ARN:-}\" ]] && echo yes || echo no)"
        echo "ENV_FILE exists: $([[ -n \"${ENV_FILE:-}\" ]] && echo yes || echo no)"
```

結果は 4 項目とも `yes` でした。これで、Environment への登録そのものは正常と切り分けられました。

## 9.2 `on.workflow_call.secrets` を追加しただけでは解決しない

一時的に reusable workflow 側へ次を追加しました。

```yaml
on:
  workflow_call:
    secrets:
      AWS_ROLE_ARN:
        required: false
```

しかし、これだけでは Secret は渡りません。

> **一般仕様**  
> `on.workflow_call.secrets` は、caller から受け取る Secret のインターフェースを定義するものです。値そのものを生成したり、自動的に caller から転送したりする設定ではありません。caller 側で個別に `secrets:` を指定するか、利用可能な場合は `secrets: inherit` を使います。

## 9.3 今回の解決と現在の運用: `secrets: inherit`

現在の `deploy.yml` では Backend / Frontend の reusable workflow 呼び出し Job に `secrets: inherit` を付けています。

```yaml
backend:
  uses: ./.github/workflows/deploy-backend.yml
  secrets: inherit

frontend:
  uses: ./.github/workflows/deploy-frontend.yml
  secrets: inherit
```

> **今回の実測**  
> `secrets: inherit` を caller に明示した構成で `AWS_ROLE_ARN` の空問題が解消したため、現在の Repository ではこの形を採用しています。

> **一般仕様: Environment Secret との関係**  
> GitHub 公式では、reusable workflow の Job 自身に `environment:` が指定されている場合、その Job ではその Environment の Secret が使用されると説明されています。一方、`secrets: inherit` は caller が利用できる Secret を called workflow へ渡す仕組みです。  
> したがって、**「Environment Secret を使うには必ず `secrets: inherit` が必要」ではありません**。今回の実測結果を GitHub Actions 全般のルールとして一般化せず、caller / called workflow の `environment:`、Secret のスコープ、渡し方を合わせて確認します。

現在の構成では、called workflow 側の Deploy Job も Environment を明示しています。

```yaml
build-and-deploy:
  environment:
    name: ${{ inputs.target_environment }}
```

このため、設計を読むときは次の2つを分けます。

```text
secrets: inherit
  -> Workflow 境界で Secret を渡す仕組み

called workflow の environment:
  -> dev / prd Environment を Job に適用する仕組み
```

### トラブルシュート用の安全な存在確認

Secret 値そのものを出さずに確認します。

```yaml
- run: echo "ROLE_ARN set: ${{ secrets.AWS_ROLE_ARN != '' }}"
```

または shell で空判定します。

**Secret の値そのものを `echo` しない**ことが重要です。

### Secret の存在確認パターン

Secret 値そのものを出力せずに確認するには、上記の shell 空判定パターンを使います。

## 9.4 Reusable Workflow の `permissions` は caller が上限になる

OIDC では `id-token: write` が必要です。Reusable Workflow では caller 側の call Job と called workflow 側の両方で必要権限を確認します。

Caller:

```yaml
backend:
  permissions:
    contents: read
    id-token: write
  uses: ./.github/workflows/deploy-backend.yml
```

Called:

```yaml
permissions:
  contents: read
  id-token: write
```

> **一般仕様**  
> Called workflow は caller から与えられた `GITHUB_TOKEN` permissions を勝手に強くできません。同じか、より制限的な権限にしかできないため、OIDC に必要な `id-token: write` を呼び出し境界の両側で確認します。

---

# 10. AWS OIDC: Access Key を GitHub に保存しない

GitHub Actions から AWS へ接続するために、固定 Access Key を GitHub Secret に保存せず OIDC を使用しています。

```text
GitHub Actions
    |
    | OIDC token
    v
AWS STS
    |
    | AssumeRoleWithWebIdentity
    v
IAM Role
    |
    v
Temporary Credentials
```

Workflow には次が必要です。

```yaml
permissions:
  contents: read
  id-token: write
```

認証:

```yaml
- name: Configure AWS credentials from OIDC
  uses: aws-actions/configure-aws-credentials@v6
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ${{ vars.AWS_REGION }}
    allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}
```

`allowed-account-ids` は、取得した Credential が想定 AWS Account のものか確認する安全装置です。

---

# 11. `AssumeRoleWithWebIdentity` が拒否された問題

Secrets を解決した次に出たエラーです。

```text
Could not assume role with OIDC:
Not authorized to perform sts:AssumeRoleWithWebIdentity
```

ここで重要なのは、IAM Role の **許可ポリシー** と **信頼ポリシー** を分けて考えることです。

```text
Trust Policy
    |
    | この GitHub OIDC は Role を引き受けてよいか？
    v
AssumeRole 成功
    |
    v
Permission Policy
    |
    | Role を引き受けた後、AWS で何をしてよいか？
    v
S3 / CloudFormation / Lambda ...
```

Role に `AdministratorAccess` が付いていても、Trust Policy が OIDC Token を拒否すれば AssumeRole 自体ができません。

## 11.1 元の Trust Policy

元は概ね次の条件でした。

```json
{
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
    },
    "StringLike": {
      "token.actions.githubusercontent.com:sub": [
        "repo:hongo-daisuke/*",
        "repo:hongo-daisuke/*"
      ]
    }
  }
}
```

同じ値が 2 回ある点は単なる重複です。

## 11.2 2026 年の GitHub OIDC immutable subject 変更

GitHub.com では、2026-07-15 以降に作成された Repository などで、default OIDC `sub` に owner ID と repository ID を含む immutable 形式が使われます。

従来:

```text
repo:hongo-daisuke/nba-dashboard:environment:dev
```

immutable 形式:

```text
repo:hongo-daisuke@OWNER_ID/nba-dashboard@REPO_ID:environment:dev
```

従来の Trust Policy:

```text
repo:hongo-daisuke/*
```

は、`hongo-daisuke` の直後に `/` が来ることを期待します。

immutable 形式では直後に `@OWNER_ID` が来るため、そのままでは一致しません。

## 11.3 1 Role を複数 Repository で使う設計を維持する場合

Repository ごとに ID を追加するのではなく、Owner ID まで固定して後ろを wildcard にできます。

概念例:

```json
{
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
  },
  "StringLike": {
    "token.actions.githubusercontent.com:sub": [
      "repo:hongo-daisuke/*",
      "repo:hongo-daisuke@OWNER_ID/*"
    ]
  }
}
```

- 1 行目: 旧 subject 形式向け
- 2 行目: immutable subject 形式向け

これなら同じ owner 配下の複数 Repository を 1 Role で扱う方針を維持できます。

ただし権限範囲は広いです。特に `AdministratorAccess` と「owner 配下全 Repository」を組み合わせると、その Role が侵害された場合の影響が大きくなります。本番運用では Repository / Environment 単位に絞るか、IAM Permission Policy を必要最小限にすることを推奨します。

より厳密にする場合:

```text
repo:hongo-daisuke@OWNER_ID/nba-dashboard@REPO_ID:environment:dev
```

のように Repository と Environment まで固定します。

---

# 12. SAM Deploy で Lambda Layer が見つからなかった問題

OIDC を突破した後、SAM Deploy で次のエラーが出ました。

```text
Unable to upload artifact FrontendApiLayer
...
backend/.aws-sam/build/FrontendApiLayer does not exist
```

最初は「GitHub Actions 内で `create.sh` を実行し、`layer.zip` を作るべきか？」を検討しました。

しかし実際の原因はもっと単純でした。

Template:

```yaml
ContentUri: Layer/
```

Repository:

```text
backend/layer/
├── create.sh
└── requirements.txt
```

つまり、大文字小文字が違っていました。

```text
Layer/  !=  layer/
```

GitHub-hosted `ubuntu-latest` は Linux のため、大文字小文字を区別します。Mac の一般的なデフォルトファイルシステムではこの差が表面化しにくいため、ローカルで気づかず CI で発見される典型的なケースです。

修正:

```diff
- ContentUri: Layer/
+ ContentUri: layer/
```

これで SAM Build / Deploy が成功しました。

現在の Template では API 用の `layer/` に加えて Batch 用の `layer/batch/` も使っています。今回の教訓は FrontendApiLayer 固有ではなく、**SAM Template の `ContentUri` と Repository 上の実ディレクトリ名を大文字小文字まで一致させる**という一般的な確認ポイントとして残します。

## `layer.zip` は Git 管理するべきか

今回の構成では管理不要です。

Template に次があります。

```yaml
Metadata:
  BuildMethod: python3.13
```

そのため Source of Truth は、

```text
backend/layer/requirements.txt
```

とし、`sam build` に Layer artifact を生成させます。

```text
requirements.txt
     |
     v
sam build
     |
     v
.aws-sam/build/FrontendApiLayer
     |
     v
sam deploy
```

生成物の `layer.zip` や `.aws-sam/` を Repository に入れる必要はありません。

現在の `.gitignore` でも、

```gitignore
.aws-sam/
*.zip
```

が除外されています。

`create.sh` は手動で zip を作りたいローカル補助ツールとして残せますが、通常の GitHub Actions Deploy では `sam build` と責務が重複するため実行していません。

---

# 13. S3 Deploy と CloudFront の構成

Frontend は **CloudFront + OAC + 非公開 S3** で配信します。

```text
Browser
   |
   v
CloudFront
   |
   | OAC / SigV4
   v
Private S3 Bucket
├── index.html
└── assets/
```

S3 Static Website Hosting を直接公開する構成ではありません。S3 の Public Access Block は有効のままにし、Bucket Policy では対象 CloudFront Distribution からの `s3:GetObject` のみを許可します。

## S3 は Bucket root へ Deploy する

Vite の Build 成果物 `frontend/dist/` は Bucket のルートへ同期します。

```bash
aws s3 sync \
  frontend/dist/ \
  "s3://${FRONTEND_BUCKET_NAME}/" \
  --delete \
  --only-show-errors
```

Deploy 後のイメージ:

```text
S3 Bucket
├── index.html
└── assets/
    ├── index-xxxx.js
    └── index-xxxx.css
```

以前のような特定 prefix を配信ルートにする設計や、S3 内に Deploy 前バックアップ用 prefix を持つ設計は採用しません。ロールバックが必要な場合は、正常だった commit へ revert して再 Deploy する方針です。

## CloudFront Origin は S3 Bucket root

CloudFront の Origin に `OriginPath` は設定しません。

```yaml
Origins:
  - Id: FrontendS3Origin
    DomainName: !GetAtt FrontendBucket.RegionalDomainName
    OriginAccessControlId: !GetAtt FrontendOAC.Id
    S3OriginConfig: {}
```

`DefaultRootObject` は `index.html` です。

```yaml
DefaultRootObject: index.html
```

Vue Router など SPA の History Mode で直接 URL へアクセスした場合に備え、現在の Template では 403 / 404 を `/index.html` へフォールバックします。

```yaml
CustomErrorResponses:
  - ErrorCode: 403
    ResponseCode: 200
    ResponsePagePath: /index.html
  - ErrorCode: 404
    ResponseCode: 200
    ResponsePagePath: /index.html
```

## Bucket Policy は CloudFront OAC に限定する

CloudFront から Bucket 内オブジェクトを取得できるよう、Bucket Policy は次の考え方です。

```yaml
Principal:
  Service: cloudfront.amazonaws.com
Action: s3:GetObject
Resource: !Sub '${FrontendBucket.Arn}/*'
Condition:
  StringEquals:
    AWS:SourceArn: !Sub 'arn:aws:cloudfront::${AWS::AccountId}:distribution/${FrontendDistribution}'
```

S3 自体を Public にせず、対象 Distribution からの読み取りだけを許可します。

## Deploy 前後の安全確認

`aws s3 sync --delete` は、ローカルに存在しないオブジェクトを S3 から削除します。そのため現在の Workflow では、sync 前に `frontend/dist` の存在とファイル数を確認しています。

Deploy 後も `list-objects-v2` でオブジェクトが存在することを確認します。

## Deploy 後は CloudFront Invalidation

```bash
aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*"
```

S3 への同期後に CloudFront のキャッシュを無効化して、新しい Frontend を反映します。この処理を行う IAM Role には `cloudfront:CreateInvalidation` が必要です。

# 14. PR Check の設計

Deploy 前に PR で壊れたコードを止めるため、PR Workflow は Deploy と分離しました。

```text
.github/workflows/
├── backend-pr-check.yml
└── frontend-pr-check.yml
```

## Backend Check

Job name:

```text
Backend Check
```

実行内容:

```text
Checkout
  |
Python 3.13
  |
SAM CLI
  |
sam validate --lint
  |
sam build
```

Deploy はしないため AWS OIDC は不要です。

## Frontend Check

Job name:

```text
Frontend Check
```

実行内容:

```text
npm ci
  |
Unit Test --------+
                  |
Type Check/Build -+
                  |
                  v
         最終結果をまとめて判定
```

Test と Build に `continue-on-error: true` を使い、どちらか 1 つで即時終了せず、1 回の CI で複数の問題を見つけられるようにしています。

Test result は Artifact に保存します。

## 実際に PR Check で見つかった問題

今回の構築途中でも、PR Check が実際に次の問題を検出しました。

- `package.json` と `package-lock.json` の不整合で `npm ci` が失敗
- Axios 導入後の Unit Test / mock の不整合
- TypeScript 設定の deprecated option による Build failure

これは「CI が邪魔をした」のではなく、**merge 前に問題を検出するという本来の目的を果たした**例です。

---

# 15. GitHub Actions の配置場所でハマった問題

当初 Workflow ファイルを次に置いていました。

```text
.github/backend-pr-check.yml
.github/frontend-pr-check.yml
```

この状態では GitHub Actions の Workflow として認識されません。

正しい配置:

```text
.github/workflows/backend-pr-check.yml
.github/workflows/frontend-pr-check.yml
```

GitHub Actions の Workflow file は `.github/workflows/` 配下へ置く必要があります。

このミスにより Required Check が、

```text
Expected - Waiting for status to be reported
```

のまま進まない状態になりました。

実際に全 Workflow を `.github/workflows/` へ移動することで、この問題を解消しました。

---

# 16. GitHub New Branch Rules / Rulesets

今回 Repository では、Rulesets を 2 層に分ける設計にしました。

```text
base-branch-protection
  -> main + dev

main-strict-protection
  -> main
```

複数 Ruleset が同じ branch に適用される場合、GitHub はルールを重ねて評価します。そのため main には base と main-strict の両方が適用されます。

## 必須 Status Check

今回 Required Check として使う Job name は次の 2 つです。

```text
Backend Check
Frontend Check
```

PR Workflow 側でも、

```yaml
name: Backend Check
```

```yaml
name: Frontend Check
```

と Job name を固定しています。

Ruleset の Required Status Check で登録する名前と Job name がずれると、実際の Workflow が成功していても Ruleset が待ち続ける原因になります。

## 設定の考え方

```text
feature/*
    |
    +--> PR to dev/main
             |
             +--> Backend Check
             +--> Frontend Check
             |
             +--> Required checks pass
                         |
                         v
                       merge
```

`main` は本番につながるため、`dev` より厳しいルールを追加できるよう `main-strict-protection` を分離しています。

### Bypass

管理者などの bypass を許可する場合でも、通常の開発フローでは bypass を前提にしないことが大切です。緊急時用の逃げ道と通常運用を分けます。

---

# 17. GitHub Environment と Ruleset は役割が違う

混同しやすいので分けます。

## Ruleset

「branch へ変更を入れてよいか」を守ります。

```text
PR
  |
  +--> Review / Required checks
  |
  +--> Merge permission
```

## Environment

「どの環境へ Deploy してよいか」を守ります。

```text
Deploy Job
   |
   +--> branch restriction
   +--> environment secret
   +--> approval (optional)
   |
   +--> AWS deploy
```

両方設定すると、

```text
コードを main に入れる gate
+
prd に deploy する gate
```

を分離できます。

---

# 18. Concurrency の考え方

Deploy は同じ環境へ同時実行させないようにします。

```yaml
concurrency:
  group: hongo-nba-dashboard-deploy-${{ github.ref == 'refs/heads/main' && 'prd' || 'dev' }}
  cancel-in-progress: false
```

```text
Run A -> dev deploy (running)
Run B -> dev deploy (waiting)
```

`cancel-in-progress: false` にしている理由は、CloudFormation / S3 更新を途中で止めて中途半端な状態にするリスクを避けるためです。

PR Check は逆で、古い commit の検証結果には価値が低いため、

```yaml
cancel-in-progress: true
```

にします。

```text
PR commit A check -> cancel
PR commit B check -> continue
```

用途によって concurrency の意味が異なります。

---

# 19. `samconfig.toml` を環境別設定の Source of Truth にする

現在は `ResourcePrefix=hongo`、`ProjectName=nba-dashboard` を共通とし、`dev` / `prd` を `samconfig.toml` で分けます。

```toml
[dev.deploy.parameters]
stack_name = "hongo-dev-nba-dashboard"
s3_prefix = "hongo-dev-nba-dashboard"
region = "ap-northeast-1"
capabilities = "CAPABILITY_NAMED_IAM"
parameter_overrides = "ParameterKey=ResourcePrefix,ParameterValue=hongo ParameterKey=Environment,ParameterValue=dev ParameterKey=ProjectName,ParameterValue=nba-dashboard ParameterKey=NbaCurrentSeason,ParameterValue=2025-26"

[prd.deploy.parameters]
stack_name = "hongo-prd-nba-dashboard"
s3_prefix = "hongo-prd-nba-dashboard"
region = "ap-northeast-1"
capabilities = "CAPABILITY_NAMED_IAM"
parameter_overrides = "ParameterKey=ResourcePrefix,ParameterValue=hongo ParameterKey=Environment,ParameterValue=prd ParameterKey=ProjectName,ParameterValue=nba-dashboard ParameterKey=NbaCurrentSeason,ParameterValue=2025-26"
```

Deploy は Orchestrator の `target_environment` をそのまま `--config-env` へ渡します。

```bash
sam deploy \
  --config-file samconfig.toml \
  --config-env "$TARGET_ENVIRONMENT"
```

Stack Name を GitHub Variable にコピーしません。

Backend Workflow が必要なときは Python 3.13 の `tomllib` で `samconfig.toml` を読みます。

```python
stack_name = config[target]["deploy"]["parameters"]["stack_name"]
```

このため、Stack Name / SAM Parameter の管理場所を `samconfig.toml` に寄せられます。

また `resolve_s3 = true` で SAM Deploy 用 Artifact Bucket を SAM CLI に解決させています。これは Frontend Hosting 用 S3 Bucket とは別物です。

# 20. 最終設定チェックリスト / 別プロジェクトへの横展開

この章は、旧「最終 GitHub 設定チェックリスト」と「別プロジェクトへ流用するときに変更する場所」を統合したものです。

| 分類 | `nba-dashboard` の現在値 / 方針 | 別プロジェクトで確認・変更するもの |
|---|---|---|
| Repository | `frontend/`, `backend/`, `.github/workflows/` | ディレクトリ構成、Workflow path |
| Branch | `dev`, `main`, `feature/*` | Branch 名、PR の向き先 |
| Environment | `dev`, `prd` | Environment 名、Deployment branch |
| Deploy | `dev -> dev`, `main -> prd` | Branch と Environment の対応 |
| Required Check | `Backend Check`, `Frontend Check` | Job name と Ruleset 登録名を一致させる |
| Ruleset | `base-branch-protection` / `main-strict-protection` | 対象 branch、Review、Bypass 方針 |
| Environment Secret | `AWS_ROLE_ARN`, `ENV_FILE` | Role ARN、Frontend 静的設定 |
| Environment Variable | `AWS_REGION`, `AWS_ACCOUNT_ID` | Region、Account ID |
| SAM | `ResourcePrefix=hongo`, `ProjectName=nba-dashboard`, `samconfig.toml` を環境別設定の Source of Truth にする | `ResourcePrefix`, `ProjectName`, `stack_name`, `s3_prefix`, `parameter_overrides` |
| CloudFormation Outputs | `ApiEndpoint`, `FrontendBucketName`, `CloudFrontDistributionId` | Frontend が必要とする契約値 |
| Frontend | `__API_ENDPOINT__` を Deploy 時に置換し、`frontend/dist/` を S3 Bucket root へ同期 | 環境変数名、Build script、Node version、Test command、S3 配置方式 |
| AWS OIDC | `token.actions.githubusercontent.com`, audience `sts.amazonaws.com` | Provider、Trust Policy `sub`、Permission Policy |
| IAM | 学習・検証段階では広めの権限を使用 | 本番では必要最小限へ絞る |

## Repository files

```text
.github/workflows/
├── backend-pr-check.yml
├── frontend-pr-check.yml
├── deploy.yml
├── deploy-backend.yml
└── deploy-frontend.yml
```

## Environment: dev / prd

```text
dev
├── Secrets
│   ├── AWS_ROLE_ARN
│   └── ENV_FILE
└── Variables
    ├── AWS_REGION
    └── AWS_ACCOUNT_ID

prd
├── Secrets
│   ├── AWS_ROLE_ARN
│   └── ENV_FILE
└── Variables
    ├── AWS_REGION
    └── AWS_ACCOUNT_ID
```

推奨 Deployment branch:

```text
dev -> dev
prd -> main
```

## Rulesets

```text
base-branch-protection
  target: main, dev

main-strict-protection
  target: main
```

Required checks:

```text
Backend Check
Frontend Check
```

## AWS IAM / OIDC

OIDC Provider:

```text
https://token.actions.githubusercontent.com
```

Audience:

```text
sts.amazonaws.com
```

Trust Policy では次を確認します。

- GitHub OIDC Provider を Federated Principal にする
- `sts:AssumeRoleWithWebIdentity` を許可する
- `aud` を `sts.amazonaws.com` に制限する
- `sub` を owner / repository / environment 方針に合わせて制限する
- 2026-07-15 以降に作成・rename・transfer された GitHub.com Repository では immutable subject format を確認する

## 横展開するときの確認順

```text
1. Repository / Branch 構成
2. PR Check / Ruleset
3. GitHub Environment
4. samconfig.toml / CloudFormation Outputs
5. Frontend ENV_FILE / Build script
6. AWS OIDC Trust Policy
7. IAM Permission Policy
8. Deploy を実行して Outputs / S3 / CloudFront / API を確認
```

**Workflow をそのままコピーすることより、値の Source of Truth と権限境界を新しい案件に合わせることを優先します。**

---

# 21. 最終 `deploy.yml` の要点

以下はパターンを理解するための縮約版です。

```yaml
name: Deploy

on:
  push:
    branches:
      - main
      - dev
    paths:
      - 'backend/**'
      - 'frontend/**'
      - '.github/workflows/deploy*.yml'

  workflow_dispatch:
    inputs:
      skip_test:
        type: boolean
        default: false

concurrency:
  group: app-deploy-${{ github.ref == 'refs/heads/main' && 'prd' || 'dev' }}
  cancel-in-progress: false

permissions: {}

jobs:
  prepare:
    runs-on: ubuntu-latest
    outputs:
      target_environment: ${{ steps.resolve.outputs.target_environment }}
    steps:
      - id: resolve
        run: |
          case "$GITHUB_REF_NAME" in
            main) echo "target_environment=prd" >> "$GITHUB_OUTPUT" ;;
            dev)  echo "target_environment=dev" >> "$GITHUB_OUTPUT" ;;
            *) exit 1 ;;
          esac

  backend:
    needs:
      - prepare
    permissions:
      contents: read
      id-token: write
    uses: ./.github/workflows/deploy-backend.yml
    secrets: inherit
    with:
      target_environment: ${{ needs.prepare.outputs.target_environment }}

  frontend:
    needs:
      - prepare
      - backend
    permissions:
      contents: read
      id-token: write
    uses: ./.github/workflows/deploy-frontend.yml
    secrets: inherit
    with:
      target_environment: ${{ needs.prepare.outputs.target_environment }}
      api_endpoint: ${{ needs.backend.outputs.api_endpoint }}
      frontend_bucket_name: ${{ needs.backend.outputs.frontend_bucket_name }}
      cloudfront_distribution_id: ${{ needs.backend.outputs.cloudfront_distribution_id }}
```

ポイントは、

```text
Trigger / Branch 判定 / 順序 -> deploy.yml
SAM                        -> deploy-backend.yml
Frontend                   -> deploy-frontend.yml
```

と責務を分けることです。

---

# 22. トラブルシューティング・プレイブック

## 症状: Required Check が `Expected - Waiting for status to be reported`

確認順:

```text
1. Workflow file は .github/workflows/ 配下か
2. on.pull_request の target branch は正しいか
3. paths filter で Workflow 自体が skip されていないか
4. Ruleset に登録した check name と Job name が一致しているか
```

今回の主原因:

```text
.github/*.yml に置いていた
```

修正:

```text
.github/workflows/*.yml
```

---

## 症状: `AWS_ROLE_ARN is not configured`

まず Secret の中身を表示せず存在確認します。

```text
通常 environment Job で yes?
  |
  +-- no  -> Environment 設定側
  |
  +-- yes -> reusable workflow 境界を確認
```

今回の解決:

```yaml
secrets: inherit
```

を caller の reusable workflow call Job に追加。

---

## 症状: `Not authorized to perform sts:AssumeRoleWithWebIdentity`

これは通常の AWS Permission 不足より前の問題です。

```text
AWS_ROLE_ARN 取得
    |
OIDC token
    |
AWS STS
    X
Trust Policy mismatch
```

確認:

```text
Principal Federated
Action sts:AssumeRoleWithWebIdentity
aud
sub
GitHub immutable subject format
```

`AdministratorAccess` の有無だけを見ないこと。

---

## 症状: `Unable to upload artifact FrontendApiLayer`

確認:

```text
ContentUri の path
実 directory の path
大文字 / 小文字
sam build の artifact
```

今回:

```text
Layer/ -> layer/
```

---

## 症状: `npm ci` failure

確認:

```text
package.json
package-lock.json
```

依存追加後に lock file を更新していないと CI が止まります。

---

## 症状: Unit Test / Build failure

`continue-on-error` を使っている場合、最後の結果判定 Step を確認します。

今回、テストと Build の両方を実行してから最終 failure にする構成にしたことで、1 回の CI で複数問題を確認できました。

---

# 23. 構築の時系列と、最終的に残った学び

Git 履歴と実際のトラブルシュートを合わせると、大きな流れは次のとおりです。

| 時点 | 内容 | 学び |
|---|---|---|
| 初期 | Frontend / Backend 独立 Deploy | 単独では分かりやすいが依存順序を表現できない |
| 設計変更 | Orchestrator + reusable workflow | Deploy の入口と実処理を分離 |
| 設計変更 | feature deploy を廃止 | shared dev environment の上書きを防ぐ |
| Rulesets / PR Check | main/dev を保護 | merge 前に Build / Test 問題を止める |
| 配置修正 | `.github/` -> `.github/workflows/` | Workflow discovery の基本 |
| Frontend CI | lock/test/TypeScript の問題発見 | CI が品質 gate として機能 |
| CFN Outputs | API/S3/CloudFront を output 化 | 手入力・二重管理を減らす |
| Bootstrap 解消 | `__API_ENDPOINT__` | 初回 Deploy を 1 Run で成立させる |
| Secret Debug | vars OK / secrets NG | Environment と reusable workflow の境界を切り分ける |
| Secret Fix | `secrets: inherit` を採用 | 今回の Repository ではこの構成で問題が解消 |
| OIDC Error | AssumeRoleWithWebIdentity failure | Permission と Trust を分けて考える |
| OIDC Fix | immutable subject に Trust を対応 | 2026 GitHub OIDC 変更へ追従 |
| SAM Error | Layer artifact missing | Linux の path case sensitivity |
| SAM Fix | `Layer/` -> `layer/` | Build artifact は Git 管理しない |
| 完了 | Backend / Frontend Deploy 成功 | Browser 表示・API Call を確認 |

Git 履歴からも、**Workflow 分割 → 配置修正 → Secret 問題の切り分け → Layer パス修正 → Deploy 成功**という変更の流れを確認できます。

その後は DynamoDB、NBA データ取得 Batch、画面・API 機能などアプリケーション側の拡張が続いていますが、`.github/workflows/` の基本構成は維持されています。

完成した YAML だけを見ると、次の理由は分かりません。

- なぜ Deploy を 3 Workflow に分けたのか
- なぜ Backend を先に実行するのか
- なぜ API URL / S3 Bucket / CloudFront ID を GitHub Variable に持たないのか
- なぜ `ENV_FILE` にプレースホルダーがあるのか
- なぜ OIDC の Trust Policy で `sub` が重要なのか

この資料で残したいのは YAML そのものより、**その設計判断と切り分け方**です。

別プロジェクトでは、次の順に設計すると流用しやすくなります。

```text
Repository構成
  -> Branch戦略
  -> PR Gate
  -> Environment
  -> Deploy順序
  -> Infrastructure Outputs
  -> Authentication
  -> Runtime Build
  -> Deployment
```

---

# 24. 本番適用前 TODO / Known Issues

現在の構成は実際に Deploy まで成功しています。ただし、**動くこと**と**本番運用へそのまま持ち込めること**は分けて考えます。

## 24.1 本番適用前に解消する TODO

### IAM Permission を最小権限化する

学習・検証段階で `AdministratorAccess` のような広い権限を使っている場合、本番では CloudFormation / Lambda / API Gateway / IAM / S3 / CloudFront / DynamoDB / Scheduler など、実際に Deploy に必要な操作へ絞ります。

特に OIDC Trust Policy の対象範囲と Permission Policy の強さを両方広くしないことが重要です。

## 24.2 Known Issues / 将来の改善候補

### Action version の固定方針

Marketplace Action を major tag で追従するか、commit SHA で pin するかをチーム方針として決めます。

### prd approval

必要なら `prd` Environment に Required Reviewer を設定します。Backend と Frontend の両方が Environment を参照するため、承認回数・再実行時の UX を実際の Workflow で確認して運用ルールを決めます。

### Deploy の path 最適化

現在は Frontend-only change でも Backend の empty changeset を通します。デプロイ時間が問題になった場合のみ、変更ファイルによる skip を検討します。

Backend を skip する場合は、Frontend が必要とする CloudFormation Outputs をどこから取得するかという別の設計が必要になるため、単純さを失ってまで早期最適化しません。

---

# 25. 最終的な設計原則

今回の構築で最終的に残った考え方を短くまとめると、次です。

### 1. Deploy の入口は 1 つにする

```text
deploy.yml
```

が branch / environment / order を決める。

### 2. 実処理は責務で分ける

```text
deploy-backend.yml
deploy-frontend.yml
```

### 3. Backend を先にする

Frontend は Backend が作る値に依存するため。

### 4. AWS が作った値は AWS から取る

```text
CloudFormation Outputs
```

を使い、GitHub への手入力を減らす。

### 5. Environment は設定とデプロイ境界に使う

```text
dev / prd
```

### 6. Secret / Environment のスコープを明示する

今回の構成では caller に `secrets: inherit` を置き、called workflow の Deploy Job では `environment: dev / prd` を適用しています。`secrets: inherit` と Environment Secret は同じ仕組みではないため、用途を分けて理解します。

### 7. AWS 認証は OIDC

固定 Access Key を GitHub に保存しない。

### 8. IAM は Permission と Trust を分けて考える

`AdministratorAccess` でも Trust が間違えば AssumeRole できない。

### 9. Build artifact は Git 管理しない

```text
requirements.txt -> sam build -> artifact
```

### 10. PR Check と Deploy は分ける

```text
merge 前の品質 gate
!=
AWS への deployment
```

---

# 26. 参考: 公式ドキュメント

本資料の仕様確認に使用した公式情報です。GitHub Actions / AWS は継続的に更新されるため、別プロジェクトへ展開するときは最新ドキュメントも確認してください。

## GitHub Actions

- GitHub Actions workflow files (`.github/workflows`)  
  https://docs.github.com/en/actions/get-started/quickstart

- Reusing workflows / `secrets: inherit`  
  https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows

- Workflow syntax / `permissions`  
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

- Environments / Environment secrets / variables  
  https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments

- Rulesets  
  https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets

- Required status checks  
  https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

- Troubleshooting required checks  
  https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks

- GitHub Actions OIDC reference / immutable subject claims  
  https://docs.github.com/en/actions/reference/security/oidc

- GitHub OIDC with AWS  
  https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws

- GitHub Changelog: immutable OIDC subject claims  
  https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens/

## Vite

- Env Variables and Modes / Protecting secrets  
  https://vite.dev/guide/env-and-mode

## AWS

- Create IAM role for OIDC federation  
  https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html

- AWS SAM: Building Lambda layers  
  https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/building-layers.html

- AWS SAM: `sam build`  
  https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-build.html

- AWS SAM: Deploy  
  https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/using-sam-cli-deploy.html

---
