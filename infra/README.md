# Infrastructure

Azure infrastructure templates for Talent Reconnect Agent.

## Choose Your Deployment Mode

| Mode | Folder | Use Case |
|------|--------|----------|
| **Public** | `infra/public/` | Demo, development, quick start |
| **Private** | `infra/private/` | Enterprise, production, compliance |

---

## 🌐 Public Infrastructure (Recommended for Demos)

All resources have **public endpoints** - no VNet, no private endpoints, no firewall complexity.

```bash
cd infra/public
./deploy.sh rg-talent-reconnect swedencentral
```

**Deployed Resources:**
- Azure AI Foundry (AI Services + Project)
- Azure AI Search (semantic search)
- Cosmos DB (session storage)
- Storage Account (Foundry data)
- Container Apps (app hosting)
- API Management (Consumption tier)
- Application Insights

**When to use:**
- ✅ Demos and POCs
- ✅ Development environments
- ✅ Quick start / learning
- ✅ Cost-conscious deployments

See [public/README.md](public/README.md) for details.

---

## 🔒 Private Infrastructure (Enterprise)

Full **network isolation** with VNet, private endpoints, and App Gateway with WAF.

```bash
cd infra/private

# 1. Deploy core AI resources
az deployment group create \
  --resource-group rg-talent-reconnect \
  --template-file main.bicep \
  --parameters main.bicepparam

# 2. Deploy network security layer
az deployment group create \
  --resource-group rg-talent-reconnect \
  --template-file network-security.bicep \
  --parameters network-security.bicepparam

# 3. Deploy app hosting
az deployment group create \
  --resource-group rg-talent-reconnect \
  --template-file app-hosting.bicep \
  --parameters app-hosting.bicepparam
```

**Deployed Resources:**
- Everything in Public, PLUS:
- Virtual Network with subnets
- Private Endpoints for all services
- App Gateway with WAF v2
- Private DNS Zones
- Network Security Groups

**When to use:**
- ✅ Production workloads
- ✅ Compliance requirements (HIPAA, SOC2, etc.)
- ✅ Enterprise security policies
- ✅ Data residency requirements

See [private/README.md](private/README.md) for details.

---

## Comparison

| Feature | Public | Private |
|---------|--------|---------|
| Deployment time | ~10 min | ~30 min |
| Monthly cost | ~$50-100 | ~$200-500 |
| Network isolation | ❌ | ✅ |
| Private endpoints | ❌ | ✅ |
| WAF protection | ❌ | ✅ |
| VNet integration | ❌ | ✅ |
| Complexity | Low | High |

---

## Post-Deployment

After deploying either mode:

```bash
# 1. Get the AI Search API key
az search admin-key show \
  --resource-group rg-talent-reconnect \
  --service-name <search-name> \
  --query primaryKey -o tsv

# 2. Update .env with endpoints
cp .env.azure .env
# Add SEARCH_SERVICE_API_KEY=<key>

# 3. Create indexes and upload data
python data/01-create-index.py
python data/02-push-data.py --count 10000
python data/03-create-feedback-index.py
python data/04-push-feedback-data.py

# 4. Run the app
python main.py
```
