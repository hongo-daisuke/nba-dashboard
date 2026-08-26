# NBA Dashboard

GitHub Actions + AWS SAM を使った **CI/CD 学習・検証用のモノレポ**です。

NBA ダッシュボードを題材に、Frontend / Backend の PR Check、GitHub Environments、AWS OIDC、SAM / CloudFormation、S3 / CloudFront へのデプロイまでを一連の構成として実装しています。

> CI/CD の設計理由、モノレポ / ポリレポ比較、Rulesets、Reusable Workflow、OIDC / IAM、実際に発生したエラーと解決方法、別プロジェクトへの横展開は  
> [GitHub Actions + AWS SAM CI/CD 設計・構築ナレッジ](docs/github-actions-aws-sam-cicd-knowledge.md) を参照してください。

---

## 1. システム全体像

```text
Browser
   |
   +----------------------> CloudFront -> Private S3 -> Vue / Vite SPA
   |
   +----------------------> API Gateway
                               |
                               v
                          API Lambda
                               |
                               v
                            DynamoDB

EventBridge Scheduler
   |
   v
Batch Lambda
   |
   +--> ESPN Public API
   |
   v
DynamoDB
```

Batch Lambda が NBA データを取得して DynamoDB へ保存し、API Lambda が保存済みデータを読み取って Frontend へ返します。

### 技術スタック

| 分類 | 技術 |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Vue Router, Pinia, Element Plus, Axios |
| Test | Vitest, Vue Test Utils |
| Backend | Python 3.13, AWS Lambda, API Gateway, aws-lambda-powertools |
| Data | DynamoDB, ESPN Public JSON API |
| Hosting | Amazon S3, Amazon CloudFront |
| Scheduler | EventBridge Scheduler (`ScheduleV2`) |
| Infrastructure as Code | AWS SAM, CloudFormation |
| CI/CD | GitHub Actions, GitHub Environments |
| AWS Authentication | GitHub Actions OIDC |

---

## 2. 主な機能

- チーム一覧
- 選手一覧
- 試合一覧
- 試合詳細 / ボックススコア
- カンファレンス順位表
- スタッツリーダーボード

NBA データ取得元の比較や DynamoDB のデータ設計については、  
[データソース選定の記録](docs/data-sources.md) を参照してください。

---

## 3. Repository 構成

```text
nba-dashboard/
├── frontend/
│   ├── src/
│   │   └── features/nba/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── lambda_functions/
│   │   ├── frontend_api/
│   │   └── nba_batch/
│   ├── layer/
│   ├── template.yaml
│   └── samconfig.toml
│
├── .github/
│   └── workflows/
│       ├── backend-pr-check.yml
│       ├── frontend-pr-check.yml
│       ├── deploy.yml
│       ├── deploy-backend.yml
│       └── deploy-frontend.yml
│
├── docs/
│   ├── github-actions-aws-sam-cicd-knowledge.md
│   └── data-sources.md
│
├── pull_request_template.md
└── README.md
```

Frontend と Backend を同じ Repository で管理する **モノレポ構成**です。

Backend Deploy 後に確定する API Endpoint / S3 Bucket / CloudFront Distribution ID を Frontend Deploy が利用するため、同じ Repository 内で Deploy の順序と値の受け渡しを管理しやすい構成にしています。

---

## 4. CI/CD 全体像

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
                         |
                         v
                      deploy.yml
                         |
                         v
                  deploy-backend.yml
                         |
                         | CloudFormation Outputs
                         v
                  deploy-frontend.yml
                         |
                         v
                   S3 / CloudFront
```

`feature/*` は共有環境へ直接 Deploy せず、PR Check を通して `dev` / `main` へ Merge された後に Deploy します。

Deploy の入口は `deploy.yml` に一本化し、**Backend -> Frontend** の順序を保証しています。

---

## 5. Branch / Environment

| Branch | PR Check | Deploy | GitHub Environment | SAM config-env |
|---|---:|---:|---|---|
| `feature/*` | Yes | No | - | - |
| `dev` | Yes | Yes | `dev` | `dev` |
| `main` | Yes | Yes | `prd` | `prd` |

基本フロー:

```text
feature/* -> PR -> dev -> dev Deploy -> PR -> main -> prd Deploy
```

`workflow_dispatch` による手動 Deploy も可能ですが、Deploy 対象 Branch は `dev` / `main` に限定します。

GitHub Environment 側でも Deployment branch を次のように制限する想定です。

```text
dev -> dev
prd -> main
```

---

## 6. GitHub Actions Workflow

| Workflow | 役割 |
|---|---|
| `backend-pr-check.yml` | PR 時に `sam validate --lint` / `sam build` を実行 |
| `frontend-pr-check.yml` | PR 時に Unit Test / Type Check / Vite Build を実行 |
| `deploy.yml` | Deploy の入口。Branch / Environment の決定と実行順序を制御 |
| `deploy-backend.yml` | OIDC 認証、SAM Validate / Build / Deploy、CloudFormation Outputs 取得 |
| `deploy-frontend.yml` | Unit Test、`.env` 生成、Vite Build、S3 Deploy、CloudFront Invalidation |

Deploy Workflow は `backend/**`、`frontend/**`、Deploy Workflow 自体の変更を契機に起動します。

README など、デプロイに関係しないファイルだけの変更では自動 Deploy しません。

---

## 7. Backend -> Frontend の値の受け渡し

Frontend が必要とする AWS Resource 情報は GitHub Variables へ手入力せず、Backend Deploy 後の CloudFormation Outputs から取得します。

```text
SAM Deploy
   |
   v
CloudFormation Outputs
   |
   +--> ApiEndpoint
   +--> FrontendBucketName
   +--> CloudFrontDistributionId
   |
   v
Frontend Workflow
```

これにより、次の値を GitHub Variables として二重管理しません。

```text
API Gateway URL
S3 Bucket Name
CloudFront Distribution ID
```

`Stack Name` は `backend/samconfig.toml` を Source of Truth とします。

### API Endpoint の受け渡し

Frontend の `ENV_FILE` には API Gateway の実 URL を固定で保存せず、Placeholder を設定します。

```dotenv
VITE_API_BASE_URL=__API_ENDPOINT__
```

Backend Deploy 後に取得した CloudFormation Output `ApiEndpoint` で `__API_ENDPOINT__` を置換し、Build 用の `.env` を一時生成します。

```text
SAM Deploy
   |
   v
ApiEndpoint
   |
   v
ENV_FILE の __API_ENDPOINT__ を置換
   |
   v
frontend/.env を一時生成
   |
   v
Vite Build
```

これにより、初回 Deploy でも Backend -> Frontend を 1 回の Deploy Workflow でつなげられます。

> `VITE_*` の値はビルド後のクライアント Bundle に含まれるため、API Key / Password / Secret Key などの機密情報は設定しません。

---

## 8. GitHub Environment

Repository の **Settings -> Environments** から `dev` / `prd` を作成します。

各 Environment で使用する値は次の 4 つです。

### Secrets

| Key | 用途 |
|---|---|
| `AWS_ROLE_ARN` | OIDC で Assume する IAM Role |
| `ENV_FILE` | Frontend Build 用の環境設定 |

### Variables

| Key | 用途 |
|---|---|
| `AWS_REGION` | AWS Region |
| `AWS_ACCOUNT_ID` | 接続先 AWS Account の検証 |

`prd` も同じキー名を使用し、Environment ごとに値を切り替えます。

---

## 9. AWS 認証

GitHub Actions から AWS への認証には **OIDC** を使用します。

```text
GitHub Actions
   |
   | OIDC Token
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

固定の AWS Access Key / Secret Access Key は GitHub Secrets に保存しません。

Workflow では OIDC 利用のため、次の Permission を使用します。

```yaml
permissions:
  contents: read
  id-token: write
```

AWS 側の OIDC Provider / IAM Role / Trust Policy、GitHub OIDC の subject format などの詳細は  
[CI/CD 設計・構築ナレッジ](docs/github-actions-aws-sam-cicd-knowledge.md) を参照してください。

---

## 10. Pull Request Check / Rulesets

`main` / `dev` 向け Pull Request では、次の Required Check を使用します。

```text
Backend Check
Frontend Check
```

Ruleset の設計方針:

```text
base-branch-protection
  target: main, dev

main-strict-protection
  target: main
```

Ruleset に登録する Required Status Check 名と Workflow の Job name は一致させます。

PR Check は AWS への Deploy を行わず、Merge 前の品質 Gate として利用します。

---

## 11. ローカル開発

### Frontend

Node.js 24 系を使用します。

```bash
cd frontend
nvm use
npm ci
npm run dev
```

ローカルで API Endpoint が必要な場合は、Git 管理対象外の `.env` に `VITE_API_BASE_URL` を設定します。

例:

```dotenv
VITE_API_BASE_URL=https://example.execute-api.ap-northeast-1.amazonaws.com/dev
```

主なコマンド:

```bash
npm run test
npm run test:watch
npm run test:coverage
npm run build
```

`.env` / `.env.*` は Git にコミットしません。サンプルは [`.env.example`](frontend/.env.example) を参照してください。

### Backend / AWS SAM

Python 3.13 / AWS SAM CLI を使用します。

```bash
cd backend
sam validate --lint
sam build
```

環境別 Deploy 設定は `backend/samconfig.toml` に定義しています。

```text
dev -> hongo-dev-nba-dashboard
prd -> hongo-prd-nba-dashboard
```

通常の環境 Deploy は GitHub Actions 経由で行います。

ローカルから Deploy する場合は、対象 AWS Account / IAM 権限を確認した上で実行します。

```bash
sam deploy --config-env dev
sam deploy --config-env prd
```

---

## 12. DynamoDB / Batch

SAM Template では NBA データを DynamoDB に保存し、Batch Lambda と API Lambda で役割を分けています。

```text
EventBridge Scheduler
        |
        v
    Batch Lambda
     /       \
    v         v
 ESPN      DynamoDB
             |
             v
          API Lambda
             |
             v
          Frontend
```

Batch Lambda がデータ収集を担当し、API Lambda は DynamoDB の保存済みデータを参照して Frontend へ返します。

---

## 13. S3 / CloudFront

Frontend のビルド成果物は S3 Bucket のルートへ直接配置します。

```text
S3 Bucket
├── index.html
└── assets/
```

Deploy 時は次の順で更新します。

```text
frontend/dist/
      |
      v
S3 Bucket root へ sync --delete
      |
      v
CloudFront Invalidation
```

CloudFront は **OAC (Origin Access Control)** を使用して非公開 S3 から配信します。S3 Bucket にはパブリックアクセスを許可せず、CloudFront 経由のアクセスのみを許可します。

---

## 14. ドキュメント

### [GitHub Actions + AWS SAM CI/CD 設計・構築ナレッジ](docs/github-actions-aws-sam-cicd-knowledge.md)

CI/CD の設計理由や、実際に構築する中で得た知見をまとめています。

- モノレポ / ポリレポ比較
- Reusable Workflow
- Backend -> Frontend の Deploy 順序
- GitHub Environment
- `secrets: inherit`
- OIDC / IAM Trust Policy
- CloudFormation Outputs
- Frontend の `ENV_FILE`
- Ruleset / Required Status Check
- Concurrency
- SAM / Lambda Layer
- トラブルシューティング
- 別プロジェクトへの横展開
- 本番適用前 TODO / Known Issues

### [データソース選定の記録](docs/data-sources.md)

NBA データ取得元の比較、ESPN 採用理由、DynamoDB のデータモデルなどをまとめています。

---

## 15. 本番適用前の確認

この Repository は学習・検証用途を含むため、本番利用へ展開する場合は特に次を確認します。

- IAM Permission Policy を必要最小限へ絞る
- OIDC Trust Policy の Repository / Environment 範囲を必要に応じて絞る
- GitHub Environment の Deployment branch を確認する
- `main` / `dev` の Ruleset を確認する
- Required Status Check を確認する
- `prd` Environment の Approval / Required Reviewer を検討する
- Marketplace Actions の version 固定方針を決める
- トラブルシュート用の一時的な Job / Step / Log が残っていないことを確認する

---

## この README の位置づけ

この README は **Repository の入口として、現在の構成・動かし方・CI/CD の全体像を短時間で把握するための資料**です。

「なぜこの構成にしたのか」「別の構成ではどう変わるのか」「エラー時にどこを見るのか」といった詳細は、  
[CI/CD 設計・構築ナレッジ](docs/github-actions-aws-sam-cicd-knowledge.md) を参照してください。
