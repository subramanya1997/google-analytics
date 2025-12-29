# API Documentation

> **Version**: 1.0.0  
> **Base URL**: `https://api.yourdomain.com`  
> **Last Updated**: December 2025

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Common Headers](#common-headers)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Auth Service API](#auth-service-api)
- [Data Service API](#data-service-api)
- [Analytics Service API](#analytics-service-api)

---

## Overview

The Google Analytics Intelligence System exposes three RESTful API services:

| Service | Base Path | Port | Purpose |
|---------|-----------|------|---------|
| Auth Service | `/auth/api/v1` | 8003 | Authentication & tenant management |
| Data Service | `/data/api/v1` | 8002 | Data ingestion & availability |
| Analytics Service | `/analytics/api/v1` | 8001 | Dashboard & reporting |

### API Conventions

- All endpoints return JSON
- Dates use ISO 8601 format: `YYYY-MM-DD`
- Timestamps use Unix epoch (seconds)
- Pagination uses `page` and `limit` parameters
- All list endpoints support filtering

---

## Authentication

### OAuth 2.0 Flow

```
1. GET  /auth/api/v1/login           → Get OAuth login URL
2. User authenticates with IdP       → Redirect with code
3. POST /auth/api/v1/callback        → Exchange code for session
4. Use access_token for all requests
```

### Token Usage

Include the access token in all API requests:

```http
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

---

## Common Headers

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | Bearer token from authentication |
| `X-Tenant-Id` | Yes | UUID of the tenant |
| `Content-Type` | For POST/PUT | `application/json` |

### Response Headers

| Header | Description |
|--------|-------------|
| `X-Process-Time` | Request processing time in seconds |
| `Content-Type` | `application/json` |

---

## Error Handling

### Error Response Format

```json
{
  "error": "string",
  "message": "Human-readable error description",
  "details": {}
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal error |
| 503 | Service Unavailable | Dependency unavailable |

### Error Examples

**401 Unauthorized**
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired access token"
}
```

**422 Validation Error**
```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "details": {
    "start_date": "Date must be in YYYY-MM-DD format",
    "limit": "Must be between 1 and 1000"
  }
}
```

---

## Rate Limiting

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Read (GET) | 100 requests | 1 minute |
| Write (POST/PUT/DELETE) | 30 requests | 1 minute |
| Data Ingestion | 5 concurrent | - |

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1700000060
```

---

## Auth Service API

**Base URL**: `/auth/api/v1`

### GET /login

Get the OAuth login URL to initiate authentication.

**Request**
```http
GET /auth/api/v1/login
```

**Response** `200 OK`
```json
{
  "login_url": "https://idp.example.com/admin/?redirect=..."
}
```

---

### POST /callback

Exchange OAuth code for session credentials.

**Request**
```http
POST /auth/api/v1/callback
Content-Type: application/json

{
  "code": "oauth_authorization_code"
}
```

**Response** `200 OK`
```json
{
  "success": true,
  "message": "Authentication successful",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "username": "john.doe@company.com",
  "business_name": "Acme Corp",
  "access_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Error Response** `401 Unauthorized`
```json
{
  "error": "unauthorized",
  "message": "PostgreSQL connection failed - authentication cannot proceed"
}
```

---

### POST /logout

Invalidate the current session.

**Request**
```http
POST /auth/api/v1/logout
Authorization: Bearer <access_token>
```

**Response** `200 OK`
```json
{
  "success": true,
  "message": "Logout successful"
}
```

---

### GET /validate

Validate an access token and retrieve user information.

**Request**
```http
GET /auth/api/v1/validate
Authorization: Bearer <access_token>
```

**Response** `200 OK`
```json
{
  "valid": true,
  "message": "Token is valid",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "username": "john.doe@company.com",
  "business_name": "Acme Corp"
}
```

---

## Data Service API

**Base URL**: `/data/api/v1`

### POST /ingest/start

Start a new data ingestion job.

**Request**
```http
POST /data/api/v1/ingest/start
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
Content-Type: application/json

{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data_types": ["events", "users", "locations"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | string | Yes | Start date (YYYY-MM-DD) |
| `end_date` | string | Yes | End date (YYYY-MM-DD) |
| `data_types` | array | Yes | Types to ingest: `events`, `users`, `locations` |

**Response** `201 Created`
```json
{
  "job_id": "job_20240101_abc123",
  "status": "queued",
  "message": "Ingestion job created and queued"
}
```

---

### GET /ingest/jobs

List ingestion jobs for the tenant.

**Request**
```http
GET /data/api/v1/ingest/jobs?page=1&limit=20
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 50 | Items per page (max 100) |

**Response** `200 OK`
```json
{
  "data": [
    {
      "job_id": "job_20240101_abc123",
      "status": "completed",
      "data_types": ["events", "users", "locations"],
      "start_date": "2024-01-01",
      "end_date": "2024-01-31",
      "records_processed": {
        "purchase": 1523,
        "add_to_cart": 8234,
        "page_view": 125000,
        "users_processed": 5000,
        "locations_processed": 150
      },
      "created_at": "2024-02-01T08:00:00Z",
      "started_at": "2024-02-01T08:00:05Z",
      "completed_at": "2024-02-01T08:15:30Z",
      "error_message": null
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

---

### GET /ingest/{job_id}

Get status of a specific ingestion job.

**Request**
```http
GET /data/api/v1/ingest/job_20240101_abc123
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "job_id": "job_20240101_abc123",
  "status": "processing",
  "progress": {
    "current": "events",
    "events_extracted": 50000
  },
  "created_at": "2024-02-01T08:00:00Z",
  "started_at": "2024-02-01T08:00:05Z"
}
```

**Job Status Values**:
- `queued` - Job created, waiting to start
- `processing` - Job is running
- `completed` - Job finished successfully
- `failed` - Job failed with error

---

### GET /availability

Get data availability summary for the tenant.

**Request**
```http
GET /data/api/v1/availability
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "summary": {
    "earliest_date": "2023-01-01",
    "latest_date": "2024-01-31",
    "total_days": 396
  },
  "breakdown": {
    "purchase": {
      "earliest_date": "2023-01-01",
      "latest_date": "2024-01-31",
      "total_records": 45230
    },
    "add_to_cart": {
      "earliest_date": "2023-01-01",
      "latest_date": "2024-01-31",
      "total_records": 234521
    },
    "page_view": {
      "earliest_date": "2023-01-01",
      "latest_date": "2024-01-31",
      "total_records": 5234521
    }
  }
}
```

---

## Analytics Service API

**Base URL**: `/analytics/api/v1`

### GET /locations

Get all active locations for the tenant.

**Request**
```http
GET /analytics/api/v1/locations
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "locations": [
    {
      "locationId": "D01",
      "locationName": "Downtown Branch",
      "city": "New York",
      "state": "NY"
    },
    {
      "locationId": "D02",
      "locationName": "Uptown Branch",
      "city": "New York",
      "state": "NY"
    }
  ]
}
```

---

### GET /stats

Get dashboard overview statistics.

**Request**
```http
GET /analytics/api/v1/stats?start_date=2024-01-01&end_date=2024-01-31&location_id=D01
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | Yes | Start date (YYYY-MM-DD) |
| `end_date` | string | Yes | End date (YYYY-MM-DD) |
| `location_id` | string | No | Filter by location |

**Response** `200 OK`
```json
{
  "totalRevenue": 1523456.78,
  "totalPurchases": 4523,
  "totalVisitors": 125000,
  "abandonedCarts": 8234,
  "totalSearches": 45000,
  "failedSearches": 2300
}
```

---

### GET /stats/complete

Get complete dashboard data in a single call (optimized).

**Request**
```http
GET /analytics/api/v1/stats/complete?start_date=2024-01-01&end_date=2024-01-31&granularity=daily
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | Yes | Start date |
| `end_date` | string | Yes | End date |
| `granularity` | string | No | `daily`, `weekly`, `monthly` (default: `daily`) |
| `location_id` | string | No | Filter by location |

**Response** `200 OK`
```json
{
  "metrics": {
    "totalRevenue": 1523456.78,
    "totalPurchases": 4523,
    "totalVisitors": 125000,
    "abandonedCarts": 8234
  },
  "chartData": [
    {
      "date": "2024-01-01",
      "revenue": 45000.00,
      "purchases": 150,
      "visitors": 4000,
      "carts": 280
    }
  ],
  "locationStats": [
    {
      "locationId": "D01",
      "locationName": "Downtown",
      "revenue": 500000.00,
      "purchases": 1500
    }
  ]
}
```

---

### GET /tasks/purchases

Get purchase follow-up tasks.

**Request**
```http
GET /analytics/api/v1/tasks/purchases?page=1&limit=50&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `limit` | integer | No | Items per page (default: 50, max: 1000) |
| `query` | string | No | Search by customer name/email |
| `location_id` | string | No | Filter by branch |
| `start_date` | string | No | Filter by date range |
| `end_date` | string | No | Filter by date range |

**Response** `200 OK`
```json
{
  "data": [
    {
      "userId": "user_12345",
      "userName": "John Doe",
      "userEmail": "john@example.com",
      "companyName": "Acme Corp",
      "locationId": "D01",
      "locationName": "Downtown Branch",
      "lastPurchaseDate": "2024-01-15",
      "totalRevenue": 15234.50,
      "purchaseCount": 5,
      "items": [
        {
          "itemId": "SKU-001",
          "itemName": "Industrial Widget",
          "quantity": 10,
          "price": 150.00
        }
      ],
      "sessionId": "session_abc123"
    }
  ],
  "total": 523,
  "page": 1,
  "limit": 50,
  "has_more": true
}
```

---

### GET /tasks/cart-abandonment

Get cart abandonment recovery tasks.

**Request**
```http
GET /analytics/api/v1/tasks/cart-abandonment?page=1&limit=50
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "userId": "user_12345",
      "userName": "Jane Smith",
      "userEmail": "jane@example.com",
      "companyName": "Smith Industries",
      "locationId": "D02",
      "locationName": "Uptown Branch",
      "cartDate": "2024-01-20",
      "cartValue": 2340.00,
      "itemCount": 3,
      "items": [
        {
          "itemId": "SKU-002",
          "itemName": "Premium Gadget",
          "quantity": 2,
          "price": 1000.00
        }
      ],
      "daysSinceCart": 5,
      "sessionId": "session_xyz789"
    }
  ],
  "total": 234,
  "page": 1,
  "limit": 50,
  "has_more": true
}
```

---

### GET /tasks/search-analysis

Get search optimization tasks (failed searches, low-converting searches).

**Request**
```http
GET /analytics/api/v1/tasks/search-analysis?page=1&limit=50&include_converted=false
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `include_converted` | boolean | No | Include searches that led to purchase (default: false) |

**Response** `200 OK`
```json
{
  "data": [
    {
      "searchTerm": "industrial valve 3 inch",
      "searchCount": 45,
      "uniqueUsers": 32,
      "resultCount": 0,
      "conversionRate": 0.0,
      "lastSearched": "2024-01-25",
      "topLocations": ["D01", "D03"],
      "relatedSearches": ["valve 3in", "industrial valves"]
    }
  ],
  "total": 156,
  "page": 1,
  "limit": 50,
  "has_more": true
}
```

---

### GET /tasks/repeat-visits

Get repeat visitor engagement opportunities.

**Request**
```http
GET /analytics/api/v1/tasks/repeat-visits?page=1&limit=50
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "userId": "user_67890",
      "userName": "Bob Wilson",
      "userEmail": "bob@example.com",
      "companyName": "Wilson & Co",
      "locationId": "D01",
      "visitCount": 12,
      "lastVisit": "2024-01-25",
      "totalPageViews": 156,
      "averageSessionDuration": 420,
      "topViewedCategories": ["Valves", "Fittings"],
      "hasPurchased": false
    }
  ],
  "total": 89,
  "page": 1,
  "limit": 50,
  "has_more": true
}
```

---

### GET /tasks/performance

Get branch performance metrics.

**Request**
```http
GET /analytics/api/v1/tasks/performance?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "locationId": "D01",
      "locationName": "Downtown Branch",
      "revenue": 523000.00,
      "purchases": 1523,
      "visitors": 45000,
      "conversionRate": 3.38,
      "averageOrderValue": 343.40,
      "cartAbandonmentRate": 18.5,
      "topProducts": [
        {"itemId": "SKU-001", "itemName": "Widget A", "revenue": 45000}
      ]
    }
  ],
  "total": 15,
  "page": 1,
  "limit": 50,
  "has_more": false
}
```

---

### GET /history/session/{session_id}

Get event timeline for a specific session.

**Request**
```http
GET /analytics/api/v1/history/session/session_abc123
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "sessionId": "session_abc123",
  "userId": "user_12345",
  "startTime": "2024-01-15T10:30:00Z",
  "endTime": "2024-01-15T11:15:00Z",
  "events": [
    {
      "eventType": "page_view",
      "timestamp": "2024-01-15T10:30:00Z",
      "pageTitle": "Home",
      "pageUrl": "/home"
    },
    {
      "eventType": "view_search_results",
      "timestamp": "2024-01-15T10:32:00Z",
      "searchTerm": "industrial valve"
    },
    {
      "eventType": "view_item",
      "timestamp": "2024-01-15T10:35:00Z",
      "itemId": "SKU-001",
      "itemName": "Industrial Valve 3-inch"
    },
    {
      "eventType": "add_to_cart",
      "timestamp": "2024-01-15T10:40:00Z",
      "itemId": "SKU-001",
      "quantity": 5,
      "price": 150.00
    },
    {
      "eventType": "purchase",
      "timestamp": "2024-01-15T11:10:00Z",
      "transactionId": "TXN-12345",
      "revenue": 750.00
    }
  ]
}
```

---

### GET /history/user/{user_id}

Get event timeline for a specific user.

**Request**
```http
GET /analytics/api/v1/history/user/user_12345
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "userId": "user_12345",
  "userName": "John Doe",
  "userEmail": "john@example.com",
  "companyName": "Acme Corp",
  "sessions": [
    {
      "sessionId": "session_abc123",
      "date": "2024-01-15",
      "duration": 2700,
      "pageViews": 12,
      "didPurchase": true,
      "revenue": 750.00
    },
    {
      "sessionId": "session_def456",
      "date": "2024-01-10",
      "duration": 1800,
      "pageViews": 8,
      "didPurchase": false,
      "revenue": 0
    }
  ],
  "summary": {
    "totalSessions": 15,
    "totalPurchases": 5,
    "totalRevenue": 12500.00,
    "averageSessionDuration": 1500,
    "firstSeen": "2023-06-15",
    "lastSeen": "2024-01-15"
  }
}
```

---

### Email Management Endpoints

#### GET /email/mappings

Get branch-to-sales-rep email mappings.

**Request**
```http
GET /analytics/api/v1/email/mappings?branch_code=D01
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "mappings": [
    {
      "id": "uuid-123",
      "branch_code": "D01",
      "branch_name": "Downtown Branch",
      "sales_rep_email": "john.sales@company.com",
      "sales_rep_name": "John Sales",
      "is_enabled": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T00:00:00Z"
    }
  ]
}
```

---

#### POST /email/mappings

Create a new email mapping.

**Request**
```http
POST /analytics/api/v1/email/mappings
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
Content-Type: application/json

{
  "branch_code": "D01",
  "branch_name": "Downtown Branch",
  "sales_rep_email": "jane.sales@company.com",
  "sales_rep_name": "Jane Sales",
  "is_enabled": true
}
```

**Response** `201 Created`
```json
{
  "mapping_id": "uuid-456"
}
```

---

#### PUT /email/mappings/{mapping_id}

Update an email mapping.

**Request**
```http
PUT /analytics/api/v1/email/mappings/uuid-456
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
Content-Type: application/json

{
  "branch_code": "D01",
  "branch_name": "Downtown Branch",
  "sales_rep_email": "jane.sales@company.com",
  "sales_rep_name": "Jane Sales",
  "is_enabled": false
}
```

**Response** `200 OK`
```json
{
  "success": true
}
```

---

#### DELETE /email/mappings/{mapping_id}

Delete an email mapping.

**Request**
```http
DELETE /analytics/api/v1/email/mappings/uuid-456
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "success": true
}
```

---

#### POST /email/send

Trigger email report sending.

**Request**
```http
POST /analytics/api/v1/email/send
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
Content-Type: application/json

{
  "report_date": "2024-01-31",
  "branch_codes": ["D01", "D02"]
}
```

**Response** `202 Accepted`
```json
{
  "job_id": "email_job_abc123",
  "status": "queued",
  "message": "Email job created"
}
```

---

#### GET /email/jobs

Get email job history.

**Request**
```http
GET /analytics/api/v1/email/jobs?page=1&limit=20&status=completed
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "job_id": "email_job_abc123",
      "status": "completed",
      "report_date": "2024-01-31",
      "target_branches": ["D01", "D02"],
      "total_emails": 5,
      "emails_sent": 5,
      "emails_failed": 0,
      "created_at": "2024-02-01T08:00:00Z",
      "started_at": "2024-02-01T08:00:05Z",
      "completed_at": "2024-02-01T08:01:30Z"
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

---

#### GET /email/jobs/{job_id}

Get status of a specific email job.

**Request**
```http
GET /analytics/api/v1/email/jobs/email_job_abc123
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

**Response** `200 OK`
```json
{
  "job_id": "email_job_abc123",
  "status": "completed",
  "report_date": "2024-01-31",
  "target_branches": ["D01", "D02"],
  "total_emails": 5,
  "emails_sent": 5,
  "emails_failed": 0,
  "created_at": "2024-02-01T08:00:00Z",
  "completed_at": "2024-02-01T08:01:30Z"
}
```

---

## Health & Utility Endpoints

All services expose these endpoints:

### GET /health

**Response** `200 OK`
```json
{
  "service": "analytics-service",
  "version": "0.0.1",
  "status": "healthy",
  "timestamp": 1700000000.0
}
```

### GET /

**Response** `200 OK`
```json
{
  "service": "analytics-service",
  "version": "0.0.1",
  "message": "analytics-service is running",
  "docs": "/docs",
  "health": "/health"
}
```

---

## SDK Examples

### Python

```python
import httpx

class AnalyticsClient:
    def __init__(self, base_url: str, access_token: str, tenant_id: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-Id": tenant_id
        }
    
    async def get_dashboard_stats(self, start_date: str, end_date: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/analytics/api/v1/stats",
                params={"start_date": start_date, "end_date": end_date},
                headers=self.headers
            )
            return response.json()
```

### JavaScript/TypeScript

```typescript
class AnalyticsClient {
  constructor(
    private baseUrl: string,
    private accessToken: string,
    private tenantId: string
  ) {}

  private get headers() {
    return {
      'Authorization': `Bearer ${this.accessToken}`,
      'X-Tenant-Id': this.tenantId,
      'Content-Type': 'application/json'
    };
  }

  async getDashboardStats(startDate: string, endDate: string) {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    const response = await fetch(
      `${this.baseUrl}/analytics/api/v1/stats?${params}`,
      { headers: this.headers }
    );
    return response.json();
  }
}
```

### cURL

```bash
# Get dashboard stats
curl -X GET "https://api.example.com/analytics/api/v1/stats?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID"

# Start data ingestion
curl -X POST "https://api.example.com/data/api/v1/ingest/start" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-31", "data_types": ["events"]}'
```

---

## Changelog

### v1.0.0 (November 2024)
- Initial API documentation
- Auth, Data, and Analytics service endpoints documented

---

*For interactive API documentation, visit `/docs` on any running service.*

