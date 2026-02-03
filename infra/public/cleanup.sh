#!/bin/bash
# Cleanup script - Delete all Talent Reconnect resource groups
# Run with: bash cleanup.sh

set -e

echo "⚠️  This will DELETE the following resource groups:"
echo ""

RESOURCE_GROUPS=(
    "rg-talentreconnect-eastus2"
    "rg-talentreconnect-prod"
    "rg-talentreconnect-sweden"
    "ME_tragt-ca-env-4pwr_rg-talentreconnect-sweden_swedencentral"
    "rg-ai-agents-francecentral"
)

for rg in "${RESOURCE_GROUPS[@]}"; do
    if az group exists --name "$rg" 2>/dev/null | grep -q true; then
        echo "  ✗ $rg (exists)"
    else
        echo "  - $rg (not found)"
    fi
done

echo ""
read -p "Type 'DELETE' to confirm: " confirm

if [ "$confirm" != "DELETE" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🗑️  Deleting resource groups..."

for rg in "${RESOURCE_GROUPS[@]}"; do
    if az group exists --name "$rg" 2>/dev/null | grep -q true; then
        echo "  Deleting $rg..."
        az group delete --name "$rg" --yes --no-wait
    fi
done

echo ""
echo "✓ Deletion initiated (async). Check Azure Portal for status."
echo "  Resources may take 5-15 minutes to fully delete."
