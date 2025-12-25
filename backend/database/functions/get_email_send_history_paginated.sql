-- ULTRA-FAST email send history pagination function - Pure SQL for maximum performance
-- Gets email send history with total count using optimized indexes

CREATE OR REPLACE FUNCTION get_email_send_history_paginated(
    p_tenant_id uuid,
    p_limit int DEFAULT 50,
    p_offset int DEFAULT 0,
    p_branch_code varchar DEFAULT NULL,
    p_status varchar DEFAULT NULL,
    p_start_date date DEFAULT NULL,
    p_end_date date DEFAULT NULL
)
RETURNS TABLE(
    id uuid,
    job_id varchar,
    branch_code varchar,
    sales_rep_email varchar,
    sales_rep_name varchar,
    subject varchar,
    report_date date,
    status varchar,
    smtp_response text,
    error_message text,
    sent_at timestamptz,
    total_count bigint
) LANGUAGE sql STABLE AS $$
    -- Single optimized query using window function and index
    SELECT 
        id,
        job_id,
        branch_code,
        sales_rep_email,
        sales_rep_name,
        subject,
        report_date,
        status,
        smtp_response,
        error_message,
        sent_at,
        COUNT(*) OVER() AS total_count
    FROM email_send_history
    WHERE tenant_id = p_tenant_id
        AND (p_branch_code IS NULL OR branch_code = p_branch_code)
        AND (p_status IS NULL OR status = p_status)
        AND (p_start_date IS NULL OR report_date >= p_start_date)
        AND (p_end_date IS NULL OR report_date <= p_end_date)
    ORDER BY sent_at DESC  -- Uses idx_email_history_tenant_date index
    LIMIT p_limit
    OFFSET p_offset;
$$;
