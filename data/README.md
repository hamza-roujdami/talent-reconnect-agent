# Azure AI Search Bootstrap

Use this folder to stand up the Azure AI Search pieces that power the talent-reconnect agents. The flow is intentionally short: create the service, define the `resumes` index, and ingest synthetic resumes so the agents have data to retrieve.

---

## 0. Prerequisites

| Requirement | How to get it |
|-------------|---------------|
| Azure subscription | [Create a free account](https://azure.microsoft.com/free/) |
| Azure CLI (optional but recommended) | `brew install azure-cli` or [install guide](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| Python 3.9+ with pip | `brew install python` or [python.org](https://python.org) |
| Python libs | `pip install -r requirements.txt` (includes `azure-search-documents` + `faker`) |

> 💡 Sign in with `az login` so the Azure CLI commands below work.

---

## 1. Create the Azure AI Search service

You can create the Search service in the portal or via CLI. Replace the placeholders with your resource-group name and a globally unique service name.

```bash
# Create a resource group (only once)
az group create \
  --name talent-reconnect-rg \
  --location uaenorth

# Create the search service
az search service create \
  --name talent-reconnect-search \
  --resource-group talent-reconnect-rg \
  --sku standard \
  --location uaenorth
```

Record the Search endpoint and admin key from **Azure Portal → Search service → Settings → Keys**:

```bash
AZURE_SEARCH_ENDPOINT=https://talent-reconnect-search.search.windows.net
AZURE_SEARCH_API_KEY=<your-admin-key>  # legacy AZURE_SEARCH_KEY still works
```

Add those values to your project `.env` so the scripts can authenticate.

---

## 2. Create the `resumes` index

The schema (fields, attributes, semantic config) lives in [01-create-index.py](01-create-index.py). Run it once after setting the env vars:

```bash
python data/01-create-index.py
```

The script will delete any existing `resumes` index before re-creating it, so you can re-run it safely during development.

---

## 3. Generate & upload synthetic resumes

[02-push-data.py](02-push-data.py) produces realistic-but-fake resumes using Faker and uploads them directly to the index.

```bash
# Dry run to preview a sample document
python data/02-push-data.py --count 1000 --dry-run

# Generate and upload 100k resumes (takes a few minutes)
python data/02-push-data.py --count 100000
```

The generator covers multiple roles (engineering, data, product, management) and locations weighted toward the UAE, so the demo agents have meaningful variety.

---

## 4. (Optional) Create the `feedback` index

If you want the scoring agent to ground interview feedback, create the auxiliary `feedback` index defined in [03-create-feedback-index.py](03-create-feedback-index.py):

```bash
python data/03-create-feedback-index.py
```

This schema links feedback records back to the primary `resumes` documents via `candidate_id`.

> 📌 Add `AZURE_FEEDBACK_INDEX_NAME=feedback` to your `.env` (or export it) so the insights agent and harness scripts know which index to query.

---

## 5. (Optional) Upload sample feedback data

[04-push-feedback-data.py](04-push-feedback-data.py) pages through the resumes index, fabricates interview notes, and uploads them to the `feedback` index. It now guarantees at least **one feedback record per resume** so every candidate has history in Azure AI Search. Run it with the defaults (100k resumes → 100k feedback docs) or bump `--total-feedback` to sprinkle in extra interviews:

```bash
python data/04-push-feedback-data.py --total-feedback 120000 --candidate-pool 100000
```

Use `--dry-run` if you want to preview the distribution without uploading.

---

## 6. Verify

Use the Azure Portal search explorer or the numbered harness scripts (`data/05-08-*.py`) to confirm the indexes are populated. Once these steps are complete, the multi-agent workflows can rely on Azure AI Search as their knowledge source.

```bash
# Resume index harnesses
python data/05-resumes-semantic-harness.py
python data/06-resumes-agentic-harness.py

# Feedback index harnesses
python data/07-feedback-semantic-harness.py
python data/08-feedback-agentic-harness.py
```
