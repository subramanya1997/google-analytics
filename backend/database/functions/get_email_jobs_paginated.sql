-- ULTRA-FAST email jobs pagination function - Pure SQL for maximum performance
-- Gets email job history with total count using optimized indexes

CREATE OR REPLACE FUNCTION get_email_jobs_paginated(
    p_tenant_id uuid,
    p_limit int DEFAULT 50,
    p_offset int DEFAULT 0,
    p_status varchar DEFAULT NULL
)
RETURNS TABLE(
    job_id varchar,
    status varchar,
    report_date date,
    target_branches text[],
    total_emails int,
    emails_sent int,
    emails_failed int,
    error_message text,
    created_at timestamptz,
    started_at timestamptz,
    completed_at timestamptz,
    total_count bigint
) LANGUAGE sql STABLE AS $$
    -- Single optimized query using window function and index
    SELECT 
        job_id,
        status,
        report_date,
        target_branches,
        total_emails,
        emails_sent,
        emails_failed,
        error_message,
        created_at,
        started_at,
        completed_at,
        COUNT(*) OVER() AS total_count
    FROM email_sending_jobs
    WHERE tenant_id = p_tenant_id
        AND (p_status IS NULL OR status = p_status)
    ORDER BY created_at DESC  -- Uses idx_email_jobs_tenant_created index perfectly
    LIMIT p_limit
    OFFSET p_offset;
$$;

