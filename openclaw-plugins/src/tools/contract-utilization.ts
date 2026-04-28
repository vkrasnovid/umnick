import { ToolsApiClient } from '../client.js';
import type { ToolDefinition } from '../types.js';

const client = new ToolsApiClient();

const tool: ToolDefinition = {
  name: 'get_contract_utilization',
  description: 'Анализ выборки по договорам: находит договоры с темпом выборки ниже ожидаемого относительно срока действия',
  inputSchema: {
    type: 'object',
    properties: {
      contract_id: { type: 'string', description: 'ID конкретного договора (опционально)' },
      counterparty_id: { type: 'string', description: 'ID контрагента для фильтрации (опционально)' },
      utilization_below: { type: 'number', description: 'Порог выборки в процентах, ниже которого показать договоры (по умолчанию 30)' },
      days_remaining: { type: 'number', description: 'Оставшийся срок действия в днях (опционально)' },
    },
  },
  handler: async (params: Record<string, unknown>, context: { tenantId: string }) => {
    const result = await client.execute('get_contract_utilization', context.tenantId, params);
    if (!result.success) return `❌ ${result.error}`;
    
    const data = result.data as any;
    const contracts = data.contract ? [data.contract] : [];
    if (!contracts.length) return '✅ Все договоры выполняются в нормальном темпе.';

    let msg = '*📊 Контроль выборки по договорам*\n\n';
    const critical = contracts.filter((c: any) => c.utilization_pct < 20);
    const warn = contracts.filter((c: any) => c.utilization_pct >= 20 && c.utilization_pct < 40);
    
    if (critical.length) {
      msg += `🚨 *Критические*: ${critical.length} дог.\n`;
      critical.forEach((c: any) => {
        msg += `• *${c.contract_number || c.id}* — выбрано ${c.utilization_pct}% от срока\n`;
      });
    }
    if (warn.length) {
      msg += `\n⚠️ *Требуют внимания*: ${warn.length} дог.\n`;
      warn.forEach((c: any) => {
        msg += `• *${c.contract_number || c.id}* — выбрано ${c.utilization_pct}% от срока\n`;
      });
    }
    return msg;
  },
};

export default tool;
