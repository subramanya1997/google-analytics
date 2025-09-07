-- ULTRA-FAST tenant jobs pagination function - Pure SQL for maximum performance
-- Gets job history with total count using optimized indexes

CREATE OR REPLACE FUNCTION get_tenant_jobs_paginated(
    p_tenant_id uuid,
    p_limit int DEFAULT 50,
    p_offset int DEFAULT 0
)
RETURNS TABLE(
    id uuid,
    tenant_id uuid,
    job_id varchar,
    status varchar,
    data_types json,
    start_date date,
    end_date date,
    progress json,
    records_processed json,
    error_message text,
    created_at timestamptz,
    started_at timestamptz,
    completed_at timestamptz,
    total_count bigint
) LANGUAGE sql STABLE AS $$
    -- Single optimized query using window function and index
    SELECT 
        id,
        tenant_id,
        job_id,
        status,
        data_types,
        start_date,
        end_date,
        progress,
        records_processed,
        error_message,
        created_at,
        started_at,
        completed_at,
        COUNT(*) OVER() AS total_count
    FROM processing_jobs
    WHERE tenant_id = p_tenant_id
    ORDER BY created_at DESC  -- Uses idx_processing_jobs_tenant_created index perfectly
    LIMIT p_limit
    OFFSET p_offset;
$$;
