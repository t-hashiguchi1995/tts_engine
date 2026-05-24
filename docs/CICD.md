# CI/CD（GitHub Actions → Cloud Run）

[harness-engineering-template](https://github.com/t-hashiguchi1995/harness-engineering-template) と同じ **WIF シークレット名**・**tfstate バケット規約**（`{PROJECT_ID}-tfstate`）を使います。

## ワークフロー

| ファイル | トリガー | 内容 |
|---------|---------|------|
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | PR / push `main` | gitleaks + ユニットテスト |
| [`.github/workflows/terraform-validate.yml`](../.github/workflows/terraform-validate.yml) | `terraform/**` 変更 | fmt / validate / plan |
| [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) | push `main` / 手動 | Cloud Build → Terraform apply |

## 初回セットアップ（1 回）

### 0. 前提

- GCP プロジェクト作成・請求有効
- `gcloud` / `terraform` / `gh` CLI
- リポジトリ: `t-hashiguchi1995/tts_engine`（bootstrap の `github_repo` と一致させる）

### 1. Terraform state バケット（手動・テンプレート ADR 準拠）

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=asia-northeast1
./scripts/create-tfstate-bucket.sh
```

### 2. Bootstrap（WIF + API）

```bash
cd terraform/bootstrap
cp terraform.tfvars.example terraform.tfvars
# project_id, github_org/repo, app_name を編集

terraform init
terraform apply
```

### 3. GitHub Secrets / Variables

bootstrap 出力を登録:

```bash
./scripts/register-github-secrets.sh
```

または UI で [`docs/infrastructure.md`](infrastructure.md) の表どおりに登録。

**Variables（セキュリティ）**: `API_KEYS_SECRET_ID`, `RATE_LIMIT_RPM`, `MAX_UPLOAD_MB`, `ALLOWED_ORIGINS` — 詳細は [`SECURITY.md`](SECURITY.md)

### 4. GCP 側の追加設定（リポジトリ外・必須）

以下は Terraform / CI では自動化されません。**デプロイ前に手動で実施**してください。

| 項目 | 手順 |
|------|------|
| **Cloud Run L4 GPU クォータ** | GCP Console → IAM → クォータ → `Cloud Run NVIDIA L4` を対象リージョンで申請 |
| **API キー（Secret Manager）** | `scripts/setup-gcp-secrets.sh` で `tts-api-keys` に登録（デプロイ前必須） |
| **Hugging Face トークン** | 同スクリプトで `hf-token` に登録し、Variable `HF_TOKEN_SECRET_ID=hf-token` |
| **モデル初回取得** | Irodori イメージ起動時に HF から取得（トークン必須の場合あり） |
| **課金アラート** | テンプレートの `billing` モジュールは未導入。必要なら Console で予算アラートを設定 |

### 5. 初回デプロイ確認

```bash
git push origin main
# または Actions → Deploy → Run workflow
```

成功後:

```bash
cd terraform && terraform output -raw gateway_url
curl "$(terraform output -raw gateway_url)/health"
```

## デプロイの流れ（main push）

1. Cloud Build が gateway / piper / irodori の 3 イメージをビルド・push（タグ = commit SHA 先頭 7 文字）
2. Terraform が Cloud Run・IAM・AR を更新

## テンプレートとの差分

| 項目 | harness-engineering-template | tts_engine |
|------|------------------------------|------------|
| インフラ配置 | `infra/environments/dev` | `terraform/bootstrap` + `terraform/` |
| デプロイ | `deploy-cloudrun` アクション（単一 API） | Terraform（3 サービス + GPU） |
| ビルド | GitHub runner 上で `docker build` | **Cloud Build**（GPU イメージが大きいため） |
| フロント | GCS | なし（API のみ） |
| dotenvx / lefthook | あり | 未導入（任意） |

## トラブルシュート

- **WIF エラー**: `attribute.repository == "t-hashiguchi1995/tts_engine"` と実リポジトリが一致するか確認
- **403 Artifact Registry**: `APP_NAME` と Terraform `artifact_repo` が一致しているか
- **GPU スケジュール失敗**: リージョン・L4 クォータ・`irodori_min_instances` を確認
