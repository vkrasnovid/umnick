import contractUtilization from './tools/contract-utilization.js';
import overduePayments from './tools/overdue-payments.js';
import clientActivity from './tools/client-activity.js';
import querySales from './tools/query-sales.js';
import findContracts from './tools/find-contracts.js';
import client360 from './tools/client-360.js';
import activeClients from './tools/active-clients.js';

export const plugins = [
  contractUtilization,
  overduePayments,
  clientActivity,
  querySales,
  findContracts,
  client360,
  activeClients,
];

export { ToolsApiClient } from './client.js';
export type * from './types.js';
