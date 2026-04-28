import { ToolsApiClient } from '../client.js';
import type { ToolDefinition } from '../types.js';

const client = new ToolsApiClient();

const tool: ToolDefinition = {
  name: 'get_client_360',
  description: 'Полная сводка по клиенту: реквизиты, договоры, задолженность, обороты, последние операции',
  inputSchema: {
    type: 'object',
    properties: {
      client_id: { type: 'string', description: 'ID клиента (обязательно)' },
    },
    required: ['client_id'],
  },
  handler: async (params: Record<string, unknown>, context: { tenantId: string }) => {
    const result = await client.execute('get_client_360', context.tenantId, params);
    if (!result.success) return `❌ ${result.error}`;

    const data = result.data as any;
    const counterpartyName = data.counterparty?.name || 'Клиент';
    let msg = `*🏢 ${counterpartyName}*\n`;
    if (data.inn) msg += `ИНН: ${data.inn}\n`;
    msg += `\n`;
    msg += `📋 Активных договоров: ${data.contracts_active?.length || 0}\n`;
    msg += `💰 Оборот (30д): ${(data.sales_30d || 0).toLocaleString('ru-RU')} ₽\n`;
    msg += `⚠️ Просроченная ДЗ: ${(data.overdue_debt || 0).toLocaleString('ru-RU')} ₽\n`;
    msg += `📅 Последняя операция: ${data.last_activity_date || '—'}`;

    if (data.contracts_active?.length) {
      msg += `\n\n*Договоры:*\n`;
      data.contracts_active.slice(0, 5).forEach((c: any) => {
        msg += `• ${c.number || '—'}: ${c.status || '—'} | ${c.amount?.toLocaleString('ru-RU') || 0} ₽\n`;
      });
    }
    return msg;
  },
};

export default tool;
