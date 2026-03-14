-- pgTAP tests for API tables (api_groups, api_invoices) created by migrations.
begin;
select plan(4);

-- api_groups exists with expected columns
select has_table('public', 'api_groups', 'api_groups table exists');
select has_column('public', 'api_groups', 'group_name', 'api_groups.group_name exists');
select has_column('public', 'api_groups', 'api_token', 'api_groups.api_token exists');

-- api_invoices exists with deleted flag for soft-delete
select has_column('public', 'api_invoices', 'deleted', 'api_invoices.deleted exists');

select * from finish();
rollback;
