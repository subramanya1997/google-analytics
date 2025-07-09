#!/usr/bin/env node

// Script to verify data consistency across different API endpoints

const API_BASE_URL = 'http://localhost:3001/api';

interface StatsResponse {
  metrics: {
    totalRevenue: string;
    purchases: number;
    abandonedCarts: number;
    failedSearches: number;
    totalVisitors: number;
    repeatVisits: number;
  };
}

interface TasksResponse {
  tasks: any[];
  total?: number;
}

async function fetchStats(locationId?: string, dateRange?: { start: string; end: string }) {
  const params = new URLSearchParams();
  if (locationId) params.append('locationId', locationId);
  if (dateRange) {
    params.append('startDate', dateRange.start);
    params.append('endDate', dateRange.end);
  }
  
  const response = await fetch(`${API_BASE_URL}/stats?${params}`);
  return response.json() as Promise<StatsResponse>;
}

async function fetchCartAbandonmentTasks(locationId?: string, dateRange?: { start: string; end: string }) {
  const params = new URLSearchParams();
  if (locationId) params.append('locationId', locationId);
  if (dateRange) {
    params.append('startDate', dateRange.start);
    params.append('endDate', dateRange.end);
  }
  
  const response = await fetch(`${API_BASE_URL}/tasks/cart-abandonment?${params}`);
  return response.json() as Promise<TasksResponse>;
}

async function fetchPurchaseTasks(locationId?: string, dateRange?: { start: string; end: string }) {
  const params = new URLSearchParams();
  if (locationId) params.append('locationId', locationId);
  if (dateRange) {
    params.append('startDate', dateRange.start);
    params.append('endDate', dateRange.end);
  }
  
  const response = await fetch(`${API_BASE_URL}/tasks/purchases?${params}`);
  return response.json() as Promise<TasksResponse>;
}

async function verifyDataConsistency() {
  console.log('🔍 Verifying data consistency across endpoints...\n');
  
  // Test with different scenarios
  const testScenarios = [
    { name: 'All data', locationId: undefined, dateRange: undefined },
    { name: 'Last 7 days', locationId: undefined, dateRange: { start: '2025-01-03', end: '2025-01-09' } },
    { name: 'Location W001', locationId: 'W001', dateRange: undefined },
    { name: 'Location W001 last 7 days', locationId: 'W001', dateRange: { start: '2025-01-03', end: '2025-01-09' } },
  ];
  
  for (const scenario of testScenarios) {
    console.log(`\n📊 Testing: ${scenario.name}`);
    console.log('=' . repeat(50));
    
    try {
      // Fetch data from all endpoints
      const [stats, cartTasks, purchaseTasks] = await Promise.all([
        fetchStats(scenario.locationId, scenario.dateRange),
        fetchCartAbandonmentTasks(scenario.locationId, scenario.dateRange),
        fetchPurchaseTasks(scenario.locationId, scenario.dateRange),
      ]);
      
      // Compare purchases
      console.log(`\n💰 Purchases:`);
      console.log(`  - Stats endpoint: ${stats.metrics.purchases}`);
      console.log(`  - Purchase tasks: ${purchaseTasks.tasks.length}`);
      if (stats.metrics.purchases !== purchaseTasks.tasks.length) {
        console.log(`  ⚠️  Mismatch! Difference: ${Math.abs(stats.metrics.purchases - purchaseTasks.tasks.length)}`);
      } else {
        console.log(`  ✅ Consistent!`);
      }
      
      // Compare abandoned carts
      console.log(`\n🛒 Abandoned Carts:`);
      console.log(`  - Stats endpoint: ${stats.metrics.abandonedCarts}`);
      console.log(`  - Cart tasks: ${cartTasks.tasks.length}`);
      if (stats.metrics.abandonedCarts !== cartTasks.tasks.length) {
        console.log(`  ⚠️  Mismatch! Difference: ${Math.abs(stats.metrics.abandonedCarts - cartTasks.tasks.length)}`);
      } else {
        console.log(`  ✅ Consistent!`);
      }
      
      // Show revenue
      console.log(`\n💵 Total Revenue: ${stats.metrics.totalRevenue}`);
      
    } catch (error) {
      console.error(`❌ Error testing scenario: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  console.log('\n\n✅ Consistency check complete!');
}

// Run the verification
verifyDataConsistency().catch(console.error); 