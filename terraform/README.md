# Terraform — Cloud Run デプロイ

`tts-gateway`（公開）、`tts-piper`（内部 CPU）、`tts-irodori`（内部 GPU）を Terraform で管理します。

## 前提

- Terraform >= 1.5
- `gcloud` 認証済み（`gcloud auth application-default login`）
- コンテナイメージがレジストリに push 済み（[`cloudbuild.yaml`](../cloudbuild.yaml) 参照）

## 初回セットアップ

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集（project_id, image_prefix 等）

terraform init
terraform plan
terraform apply
```

## CI/CD

GitHub Actions から自動デプロイする手順は [`../docs/CICD.md`](../docs/CICD.md) を参照してください。

初回は [`bootstrap/`](bootstrap/) で WIF と Terraform 状態バケットを作成します。

## イメージのビルド（手動）

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=asia-northeast1
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_IMAGE_PREFIX=${REGION}-docker.pkg.dev/${PROJECT_ID}/tts-engine,_TAG=latest
```

`image_prefix` を空にすると `{region}-docker.pkg.dev/{project_id}/{artifact_repo}` が使われます。

## 主な変数

| 変数 | 説明 |
|------|------|
| `project_id` | GCP プロジェクト ID（必須） |
| `region` | リージョン（既定: `asia-northeast1`） |
| `image_prefix` | イメージプレフィックス（必須） |
| `image_tag` | タグ（既定: `latest`） |
| `require_api_keys` | 既定 `true` — API キー未設定時はゲートウェイ起動失敗 |
| `api_keys_secret_id` | Secret Manager の API キー secret id（既定 `tts-api-keys`） |
| `allow_unauthenticated_gateway` | インターネット向け API では `true` + Bearer 必須 |
| `gateway_invoker_members` | `allow_unauthenticated_gateway=false` 時の invoker 一覧 |
| `rate_limit_rpm` / `max_upload_mb` / `allowed_origins` | レート制限・アップロード上限・CORS |
| `irodori_gpu_type` | 既定 `nvidia-l4`（Irodori-TTS-500M-v2 向け） |
| `irodori_cpu` / `irodori_memory` | 既定 `8` / `32Gi` |
| `irodori_model_precision` | 既定 `bf16` |
| `irodori_min_instances` | 既定 `1`（GPU コールドスタート対策） |
| `hf_token_secret_id` | HF トークン Secret のリソース名 |

## 出力

```bash
terraform output gateway_url
```

## IAM 構成

- ゲートウェイ SA → Piper / Irodori に `roles/run.invoker`
- ゲートウェイは `INTERNAL_USE_IAM=true` で ID トークン付きで下流を呼び出し
- Piper / Irodori は **内部 Ingress のみ**（`INGRESS_TRAFFIC_INTERNAL_ONLY`）

## 注意

- GPU Cloud Run はリージョン・クォータ・課金（instance-based）の制約があります
- `deploy/cloudrun-*.yaml` と `scripts/deploy.sh` は非推奨です（Terraform に移行済み）
