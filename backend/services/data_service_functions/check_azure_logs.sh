#!/bin/bash
# Script to check Azure Functions logs and deployment status

FUNCTION_APP_NAME="gadataingestion"

echo "================================================"
echo "Azure Functions Diagnostics"
echo "================================================"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
echo "1. Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure"
    echo "Run: az login"
    exit 1
fi
echo "✓ Logged in"
echo ""

# Find resource group first
echo "2. Finding Resource Group..."
RESOURCE_GROUP=$(az resource list --name $FUNCTION_APP_NAME --resource-type "Microsoft.Web/sites" --query "[0].resourceGroup" -o tsv)

if [ -z "$RESOURCE_GROUP" ]; then
    echo "❌ Could not find Function App '$FUNCTION_APP_NAME'"
    echo "Please check the name or run: az functionapp list -o table"
    exit 1
fi

echo "✓ Found in Resource Group: $RESOURCE_GROUP"
echo ""

# Get Function App details
echo "3. Function App Status:"
az functionapp show --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --query "{Name:name, State:state, DefaultHostName:defaultHostName}" -o table
echo ""

# Check deployment status
echo "4. Recent Deployments:"
az functionapp deployment list --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --query "[0:3].{Status:status, Author:author, Time:receivedTime, Message:message}" -o table 2>/dev/null || echo "No deployment history available"
echo ""

# Check build configuration
echo "5. Build Configuration Settings:"
az functionapp config appsettings list --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --query "[?contains(name, 'BUILD') || contains(name, 'ORYX') || contains(name, 'SCM')].{Name:name, Value:value}" -o table
echo ""

# Stream logs (last 100 lines)
echo "6. Recent Log Entries:"
echo "Fetching logs... (Press Ctrl+C to stop)"
az webapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP &
LOG_PID=$!

# Wait a bit then kill log stream
sleep 5
kill $LOG_PID 2>/dev/null

echo ""
echo "================================================"
echo "To check what Python packages are installed:"
echo "================================================"
echo "1. Azure Portal → $FUNCTION_APP_NAME → Development Tools → Console"
echo "   Run: pip list | grep -i sql"
echo ""
echo "2. Or use SSH:"
echo "   az webapp ssh --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
echo "   Then run: pip list | grep -i sql"
echo ""
echo "3. View deployment logs in Azure Portal:"
echo "   $FUNCTION_APP_NAME → Deployment Center → View logs"
echo ""
echo "4. Check if Oryx built the app:"
echo "   Look for 'Running pip install' in deployment logs"

