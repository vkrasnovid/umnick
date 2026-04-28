export interface ToolParams {
  tenant_id: string;
}

export interface ToolResponse {
  success: boolean;
  data: unknown;
  summary: string;
  error?: string;
}

export interface ODataCredentials {
  url: string;
  username: string;
  password: string;
}

export interface ContractUtilizationParams extends ToolParams {
  contract_id?: string;
  counterparty_id?: string;
  utilization_below?: number;
  days_remaining?: number;
}

export interface OverduePaymentsParams extends ToolParams {
  threshold_days?: number;
  counterparty_id?: string;
}

export interface ClientActivityParams extends ToolParams {
  client_id: string;
  period_days?: number;
}

export interface QuerySalesParams extends ToolParams {
  period: string;
  group_by?: 'month' | 'week' | 'day' | 'counterparty' | 'nomenklature_group';
  counterparty_id?: string;
  nomenklature_group?: string;
}

export interface FindContractsParams extends ToolParams {
  number?: string;
  status?: string;
  counterparty_id?: string;
  expires_before?: string;
  min_amount?: number;
}

export interface Client360Params extends ToolParams {
  client_id: string;
}

export interface ActiveClientsParams extends ToolParams {
  min_revenue?: number;
  days?: number;
  limit?: number;
}

// Plugin definition matching @openclaw/plugin-sdk structure
export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (params: Record<string, unknown>, context: { tenantId: string }) => Promise<string>;
}
