# インフラストラクチャ

[harness-engineering-template](https://github.com/t-hashiguchi1995/harness-engineering-template) の GCP / WIF / Terraform 規約に合わせた構成です。

## ディレクトリ

```
terraform/
├── bootstrap/              # 初回のみ: WIF + API 有効化（共有基盤）
│   └── modules/github_wif/ # テンプレートと同型の WIF モジュール
├── *.tf                    # Cloud Run 3 サービス + AR + IAM
└── backend.tf              # GCS backend（バケット名は init 時に指定）

.github/workflows/
├── ci.yml                  # テスト
├── deploy.yml              # main → Cloud Build + terraform apply
└── terraform-validate.yml  # PR: fmt / validate / plan
```

テンプレートの `infra/environments/dev` に相当するのが **`terraform/bootstrap`**（WIF）と **`terraform/`**（アプリ本体）の 2 段構成です。

## Workload Identity Federation

| リソース | 用途 |
|---------|------|
| `<app>-github-pool` | GitHub OIDC プール |
| `<app>-github-provider` | `token.actions.githubusercontent.com` |
| `<app>-plan` SA | `terraform plan`（`roles/viewer`） |
| `<app>-deploy` SA | ビルド + `terraform apply` |

GitHub Secrets 名はテンプレートと同一です。

| Secret | 説明 |
|--------|------|
| `PROJECT_ID` | GCP プロジェクト ID |
| `WIF_PROVIDER` | WIF プロバイダリソース名 |
| `WIF_SA_PLAN` | plan 用 SA |
| `WIF_SA_DEPLOY` | deploy 用 SA |
| `TF_STATE_BUCKET` | tfstate 用 GCS（省略時は `{PROJECT_ID}-tfstate`） |

| Variable | 既定 | 説明 |
|----------|------|------|
| `GCP_REGION` | `asia-northeast1` | リージョン |
| `APP_NAME` | `tts-engine` | Artifact Registry リポジトリ ID |
| `HF_TOKEN_SECRET_ID` | （空） | 任意: Hugging Face トークン Secret |

## Terraform 状態（GCS）

テンプレート同様、**状態バケットは Terraform 管理外**で先に作成します。

```bash
PROJECT_ID=your-project-id ./scripts/create-tfstate-bucket.sh
```

その後 bootstrap → メイン Terraform を apply します。

## シークレット管理

```
手動 / 1Password 等（真実のソース）
    ├─ GitHub Secrets  → CI（WIF_* , PROJECT_ID, TTS_API_KEYS）
    └─ Secret Manager  → Cloud Run（HF トークン等）
```

- `.env` は gitignore 済み。`.env.template` を参照。
- ゲートウェイ API キー: GitHub Secret `TTS_API_KEYS` → `TF_VAR_api_keys`

## 必要な GCP API

bootstrap が有効化します。手動の場合:

```bash
gcloud services enable \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  cloudresourcemanager.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com run.googleapis.com storage.googleapis.com \
  secretmanager.googleapis.com
```

## Cloud Run（tts_engine 固有）

| サービス | 役割 | 備考 |
|---------|------|------|
| `tts-gateway` | 公開 API | CPU |
| `tts-piper` | Piper | 内部 Ingress |
| `tts-irodori` | Irodori | **NVIDIA L4** GPU |

テンプレートは単一 `api` サービス + GCS フロントですが、本リポジトリは **Terraform で 3 サービスを一括デプロイ**します（GPU 設定は `terraform/variables.tf`）。

## 参照

- 初回手順: [`CICD.md`](CICD.md)
- テンプレート: [`docs/infrastructure.md`](https://github.com/t-hashiguchi1995/harness-engineering-template/blob/main/docs/infrastructure.md)
