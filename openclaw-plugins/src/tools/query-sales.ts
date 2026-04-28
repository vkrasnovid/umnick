import { ToolsApiClient } from '../client.js';
import type { ToolDefinition } from '../types.js';

const client = new ToolsApiClient();

const tool: ToolDefinition = {
  name: 'query_sales',
  description: 'Анализ продаж: выручка в разрезе периода, с группировкой по месяцам/неделям/дням/контрагентам/группам',
  inputSchema: {
    type: 'object',
    properties: {
      period: { type: 'string', description: 'Период: "this_month", "last_month", "this_quarter", "this_year", "YYYY-MM:YYYY-MM" (обязательно)' },
      group_by: { type: 'string', enum: ['month', 'week', 'day', 'counterparty', 'nomenklature_group'], description: 'Способ группировки' },
      counterparty_id: { type: 'string', description: 'ID контрагента (опционально)' },
      nomenklature_group: { type: 'string', description: 'Номенклатурная группа (опционально)' },
    },
    required: ['period'],
  },
  handler: async (params: Record<string, unknown>, context: { tenantId: string }) => {
    const result = await client.execute('query_sales', context.tenantId, params);
    if (!result.success) return `❌ ${result.error}`;

    const data = result.data as any;
    const totalRevenue = data.summary?.total_revenue || 0;
    let msg = `*💹 Продажи*\n`;
    msg += `Общая выручка: *${totalRevenue.toLocaleString('ru-RU')} ₽*\n\n`;

    const breakdown = data.by_counterparty || data.by_month || [];
    if (breakdown.length) {
      breakdown.slice(0, 10).forEach((row: any) => {
        const amount = row.revenue || row.amount || 0;
        const pct = totalRevenue ? ((amount / totalRevenue) * 100).toFixed(1) : '—';
        msg += `• *${row.name || row.month || row.group}*: ${amount.toLocaleString('ru-RU')} ₽ (${pct}%)\n`;
      });
    }
    return msg;
  },
};

export default tool;
