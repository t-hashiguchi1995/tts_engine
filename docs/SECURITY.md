# セキュリティ設定ガイド

本番向けのセキュリティ設定と、**手動で行う作業**の手順です。

## セキュリティ構成（概要）

```
インターネット
    │  HTTPS + Cloud Run IAM (allUsers invoker または限定 invoker)
    ▼
tts-gateway  ── Bearer API キー必須 (Secret Manager)
    │          レート制限 / セキュリティヘッダー / CORS 制限
    │  IAM ID トークン (INTERNAL_USE_IAM=true)
    ▼
tts-piper / tts-irodori  (INGRESS_TRAFFIC_INTERNAL_ONLY)
```

| レイヤー | 対策 |
|---------|------|
| 公開 API | Bearer API キー（`require_api_keys=true`） |
| シークレット | Secret Manager（平文 env / GitHub へのキー直書き禁止） |
| バックエンド | 内部 Ingress + ゲートウェイ SA のみ `run.invoker` |
| CI | gitleaks、Trivy（deploy 時） |
| コンテナ | Artifact Registry 脆弱性スキャン |

---

## 手動設定（必須）

### 1. API キーを Secret Manager に登録

Terraform はシークレット**リソース**を作成しますが、**値**は手動で入れます。

```bash
# 例: 32 文字以上のランダムキーを 1〜3 個（カンマ区切り、改行なし）
openssl rand -hex 32 > /tmp/tts-api-keys.txt
# 複数キー: echo -n "key1,key2" > /tmp/tts-api-keys.txt

PROJECT_ID=your-gcp-project-id ./scripts/setup-gcp-secrets.sh \
  --api-keys-file /tmp/tts-api-keys.txt

rm -f /tmp/tts-api-keys.txt
```

確認:

```bash
gcloud secrets versions access latest \
  --secret=tts-api-keys \
  --project=YOUR_PROJECT_ID | wc -c
# 0 より大きいこと
```

**GitHub Secret に API キーを入れないでください。**（旧 `TTS_API_KEYS` → Terraform 直渡しは廃止）

### 2. Hugging Face トークン（Irodori・**任意**）

Irodori は起動時に Hugging Face Hub からモデル重みをダウンロードします（`Aratako/Irodori-TTS-500M-v2` 等）。

| 状況 | HF トークン |
|------|-------------|
| モデルが **公開**（現状の Aratako モデル） | **なくても動作可能**（匿名ダウンロード） |
| **レート制限**回避・安定性 | **推奨**（本番では設定推奨） |
| **ゲート付き / 非公開**モデル | **必須** |

トークンを使う場合:

```bash
echo -n "hf_xxxxxxxx" > /tmp/hf-token.txt
PROJECT_ID=thash-488104 ./scripts/setup-gcp-secrets.sh --hf-token-file /tmp/hf-token.txt
rm -f /tmp/hf-token.txt
```

GitHub **Variable**: `HF_TOKEN_SECRET_ID` = `hf-token`  
Terraform: `hf_token_secret_id = "hf-token"`

**未設定の場合**: `HF_TOKEN_SECRET_ID` Variable は登録せず、Terraform の `hf_token_secret_id` もコメントアウトのままにしてください。

### 3. Terraform 本番変数

`terraform/terraform.tfvars`（または CI の TF_VAR）:

```hcl
require_api_keys              = true
api_keys_secret_id            = "tts-api-keys"
manage_api_keys_secret        = true
allow_unauthenticated_gateway = true   # インターネット向け API の場合
# allow_unauthenticated_gateway = false  # 社内のみ: gateway_invoker_members を設定

rate_limit_rpm   = 60
max_upload_mb    = 25
allowed_origins  = ""   # ブラウザから呼ぶ場合のみ: "https://app.example.com"
```

`allow_unauthenticated_gateway = false` にする場合（より厳格）:

```hcl
allow_unauthenticated_gateway = false
gateway_invoker_members = [
  "serviceAccount:CLIENT_SA@PROJECT.iam.gserviceaccount.com",
]
```

クライアントは **Google ID トークン** で Cloud Run を呼び出し、さらに **Bearer API キー** が必要です。

### 4. GitHub Actions

| 種別 | 名前 | 備考 |
|------|------|------|
| Secret | `PROJECT_ID`, `WIF_*`, `TF_STATE_BUCKET` | [CICD.md](CICD.md) 参照 |
| Variable | `HF_TOKEN_SECRET_ID` | `hf-token` |
| ~~Secret~~ | ~~`TTS_API_KEYS`~~ | **使用しない**（Secret Manager へ） |

**推奨（手動）**: GitHub → Settings → Environments → `production`

- Required reviewers を有効化
- Deployment branches: `main` のみ
- `deploy.yml` に `environment: production` を追加する場合はリポジトリ設定後に有効化

### 5. GCP コンソール

| 項目 | 手順 |
|------|------|
| **組織ポリシー** | 公開 `allUsers` 禁止ポリシーがある場合は `allow_unauthenticated_gateway=false` + invoker 限定 |
| **監査ログ** | Admin Activity / Data Access ログを有効化 |
| **アラート** | 異常な Cloud Run リクエスト数・4xx/5xx を Monitoring で通知 |
| **キーローテーション** | 四半期ごとに `gcloud secrets versions add tts-api-keys --data-file=...` |

### 6. クライアント呼び出し

```bash
export GATEWAY_URL="https://tts-gateway-xxxxx.a.run.app"
export API_KEY="（Secret Manager に登録したキー）"

curl -sS -H "Authorization: Bearer ${API_KEY}" \
  "${GATEWAY_URL}/v1/engines"
```

---

## ローカル開発

`docker-compose.yml` では緩い設定（`REQUIRE_API_KEYS=false`）です。  
ローカルで認証を試す場合:

```bash
export TTS_API_KEYS=dev-local-only-key
export REQUIRE_API_KEYS=true
docker compose up gateway piper
```

---

## 検証チェックリスト

- [ ] `tts-api-keys` にバージョンが 1 つ以上ある
- [ ] `terraform apply` 後、キーなしで `/v1/engines` が **401**
- [ ] 正しい `Authorization: Bearer` で **200**
- [ ] Piper / Irodori URL をブラウザで直接開けない（403 / 404）
- [ ] gitleaks が CI で green

---

## 参考

- [infrastructure.md](infrastructure.md)
- [CICD.md](CICD.md)
- [harness-engineering-template / ADR-002](https://github.com/t-hashiguchi1995/harness-engineering-template/blob/main/docs/adr/ADR-002-secret-manager.md)
