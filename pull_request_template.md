# Pull Request

## 概要

<!-- この PR で何を変更したのか、簡潔に記載してください。 -->


## 変更内容

<!-- 主な変更点を箇条書きで記載してください。 -->

-
-
-


## 変更対象

該当するものにチェックしてください。

- [ ] Frontend
- [ ] Backend
- [ ] GitHub Actions
- [ ] AWS / SAM 設定
- [ ] ドキュメント
- [ ] その他


## マージ先

- [ ] `dev`
- [ ] `main`

> `main` / `dev` 向け Pull Request では、Ruleset により必要な PR Check が実行されます。


## PR 種別

- [ ] 通常変更
- [ ] 機能追加
- [ ] Bug Fix
- [ ] Refactoring
- [ ] Emergency Hotfix
- [ ] その他


## 手動動作確認

CI では確認できない、画面・API・業務フローなどの動作を確認してください。

### Frontend

- [ ] 対象画面・機能の動作を確認した
- [ ] レイアウトや表示崩れがないことを確認した
- [ ] Frontend の変更なし / 手動確認不要

### Backend

- [ ] 対象 API / Lambda の動作を確認した
- [ ] 想定する Request / Response を確認した
- [ ] Backend の変更なし / 手動確認不要


## CI

以下の Check は Ruleset により Merge 前の成功が必須です。

- `Frontend Check`
- `Backend Check`

> PR Check Workflow 自体は AWS へのデプロイを行いません。


## デプロイ影響

該当するものにチェックしてください。

- [ ] AWS へのデプロイに影響しない
- [ ] Frontend の dev デプロイに影響する
- [ ] Backend の dev デプロイに影響する
- [ ] Frontend の prd デプロイに影響する
- [ ] Backend の prd デプロイに影響する
- [ ] IAM / OIDC / Secrets / Variables に変更がある
- [ ] S3 に変更がある
- [ ] Lambda / API Gateway / SAM Template に変更がある

> Deploy Workflow の対象ブランチでは、対象パスに変更がある場合にデプロイが実行されます。
>
> - `feature/*` / `dev` → `dev`
> - `main` → `prd`


## 設定変更

Secrets / Variables / AWS 設定など、リポジトリ外で必要な変更がある場合は記載してください。

<!--
例:
- GitHub Environment `dev` に `S3_BUCKET_NAME` を追加
- GitHub Environment `prd` に `AWS_ACCOUNT_ID` を追加
- IAM Role の権限を変更
- samconfig.toml の Parameter を変更
-->

なし


## ロールバック

<!--
問題発生時の戻し方を記載してください。
不要な場合は「不要」と記載してください。

例:
- Frontend: 直前の正常 commit へ revert し、再デプロイ
- Backend: 直前の正常 commit へ revert し、再デプロイ
-->

なし


## Emergency Hotfix

`Emergency Hotfix` の場合のみ記載してください。

- 緊急リリース理由:
- Ruleset Bypass 理由:
- 影響範囲:
- ロールバック方法:
- 後追いで必要な確認 / 対応:

<!-- Emergency Hotfix でない場合は「該当なし」と記載してください。 -->

該当なし


## 確認事項

- [ ] 不要なデバッグコード・ログを残していない
- [ ] Secret / Credential / `.env` をコミットしていない
- [ ] 変更内容に不要なファイルが含まれていない
- [ ] merge 後の dev / prd への影響を確認した
- [ ] リポジトリ外の設定変更がある場合、上記「設定変更」に記載した
- [ ] ロールバック方法を確認した


## 補足

<!--
レビュアーに伝えたいこと、確認してほしい点、
スクリーンショット、関連 Issue / Ticket などがあれば記載してください。
-->
