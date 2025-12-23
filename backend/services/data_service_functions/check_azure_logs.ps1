# PowerShell script to check Azure Functions logs and deployment status

$FunctionAppName = "gadataingestion"

Write-Host "================================================" -ForegroundColor Blue
Write-Host "Azure Functions Diagnostics" -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Check if Azure CLI is installed
try {
    $null = az --version
} catch {
    Write-Host "❌ Azure CLI is not installed" -ForegroundColor Red
    Write-Host "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check if logged in
Write-Host "1. Checking Azure login status..." -ForegroundColor Yellow
try {
    $null = az account show 2>&1
    Write-Host "✓ Logged in" -ForegroundColor Green
} catch {
    Write-Host "❌ Not logged in to Azure" -ForegroundColor Red
    Write-Host "Run: az login"
    exit 1
}
Write-Host ""

# Find resource group first
Write-Host "2. Finding Resource Group..." -ForegroundColor Yellow
$ResourceGroup = az resource list --name $FunctionAppName --resource-type "Microsoft.Web/sites" --query "[0].resourceGroup" -o tsv

if ([string]::IsNullOrEmpty($ResourceGroup)) {
    Write-Host "❌ Could not find Function App '$FunctionAppName'" -ForegroundColor Red
    Write-Host "Please check the name or run: az functionapp list -o table"
    exit 1
}

Write-Host "✓ Found in Resource Group: $ResourceGroup" -ForegroundColor Green
Write-Host ""

# Get Function App details
Write-Host "3. Function App Status:" -ForegroundColor Yellow
az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query "{Name:name, State:state, DefaultHostName:defaultHostName}" -o table
Write-Host ""

# Check deployment status
Write-Host "4. Recent Deployments:" -ForegroundColor Yellow
$deployments = az functionapp deployment list --name $FunctionAppName --resource-group $ResourceGroup --query "[0:3].{Status:status, Author:author, Time:receivedTime, Message:message}" -o table 2>&1
if ($LASTEXITCODE -eq 0) {
    $deployments
} else {
    Write-Host "No deployment history available" -ForegroundColor Gray
}
Write-Host ""

# Get app settings to check build flags
Write-Host "5. Build Configuration Settings:" -ForegroundColor Yellow
az functionapp config appsettings list --name $FunctionAppName --resource-group $ResourceGroup --query "[?contains(name, 'BUILD') || contains(name, 'ORYX') || contains(name, 'SCM')].{Name:name, Value:value}" -o table
Write-Host ""

Write-Host "================================================" -ForegroundColor Blue
Write-Host "Next Steps:" -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "1. View live logs:" -ForegroundColor Yellow
Write-Host "   az webapp log tail --name $FunctionAppName --resource-group $ResourceGroup" -ForegroundColor Cyan
Write-Host ""

Write-Host "2. Check installed packages (Azure Portal):" -ForegroundColor Yellow
Write-Host "   → https://portal.azure.com" -ForegroundColor Cyan
Write-Host "   → Find: $FunctionAppName" -ForegroundColor Cyan
Write-Host "   → Development Tools → Console" -ForegroundColor Cyan
Write-Host "   → Run: python -m pip list | findstr sql" -ForegroundColor Cyan
Write-Host ""

Write-Host "3. SSH into the container:" -ForegroundColor Yellow
Write-Host "   az webapp ssh --name $FunctionAppName --resource-group $ResourceGroup" -ForegroundColor Cyan
Write-Host "   Then run: pip list | grep -i sql" -ForegroundColor Cyan
Write-Host ""

Write-Host "4. View deployment logs:" -ForegroundColor Yellow
Write-Host "   Azure Portal → $FunctionAppName → Deployment Center → Logs" -ForegroundColor Cyan
Write-Host "   Look for 'Running pip install' and 'Successfully installed sqlalchemy'" -ForegroundColor Cyan

