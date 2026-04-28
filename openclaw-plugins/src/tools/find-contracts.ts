import { ToolsApiClient } from '../client.js';
import type { ToolDefinition } from '../types.js';

const client = new ToolsApiClient();

const tool: ToolDefinition = {
  name: 'find_contracts',
  description: 'Поиск и фильтрация договоров по номеру, статусу, контрагенту, дате окончания, сумме',
  inputSchema: {
    type: 'object',
    properties: {
      number: { type: 'string', description: 'Номер договора или его часть' },
      status: { type: 'string', description: 'Статус: "active", "closed", "suspended"' },
      counterparty_id: { type: 'string', description: 'ID контрагента' },
      expires_before: { type: 'string', description: 'Истекает до даты (YYYY-MM-DD)' },
      min_amount: { type: 'number', description: 'Минимальная сумма договора' },
    },
  },
  handler: async (params: Record<string, unknown>, context: { tenantId: string }) => {
    const result = await client.execute('find_contracts', context.tenantId, params);
    if (!result.success) return `❌ ${result.error}`;

    const data = result.data as any;
    if (!data?.contracts?.length) return '🔍 Договоры по заданным критериям не найдены.';

    let msg = `*📋 Найдено договоров: ${data.total || data.contracts.length}*\n\n`;
    data.contracts.slice(0, 10).forEach((c: any) => {
      const statusEmoji = c.status === 'active' ? '🟢' : c.status === 'closed' ? '⚫' : '⏸️';
      const amount = c.amount ? `${c.amount.toLocaleString('ru-RU')} ₽` : '—';
      msg += `${statusEmoji} *${c.number || 'Без номера'}* — ${c.counterparty || '—'}\n`;
      msg += `  Сумма: ${amount} | До: ${c.date_end || '—'}\n`;
    });
    return msg;
  },
};

export default tool;
