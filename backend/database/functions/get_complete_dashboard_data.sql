-- Definition for function public.get_complete_dashboard_data (oid=217042)
CREATE OR REPLACE FUNCTION public.get_complete_dashboard_data(p_tenant_id uuid, p_start_date text, p_end_date text, p_granularity text DEFAULT 'daily'::text, p_location_id text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    overview_stats JSONB;
    chart_data JSONB;
    location_stats JSONB;
BEGIN
    -- Get overview stats
    SELECT get_dashboard_overview_stats(p_tenant_id, p_start_date, p_end_date, p_location_id)
    INTO overview_stats;
    
    -- Get chart data
    SELECT get_chart_data(p_tenant_id, p_start_date, p_end_date, p_granularity, p_location_id)
    INTO chart_data;
    
    -- Always get location stats, regardless of whether a location is selected
    SELECT get_location_stats_bulk(p_tenant_id, p_start_date, p_end_date)
    INTO location_stats;
    
    RETURN jsonb_build_object(
        'metrics', overview_stats,
        'chartData', chart_data,
        'locationStats', location_stats
    );
END;
$function$

