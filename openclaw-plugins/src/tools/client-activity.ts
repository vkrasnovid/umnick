import { ToolsApiClient } from '../client.js';
import type { ToolDefinition } from '../types.js';

const client = new ToolsApiClient();

const tool: ToolDefinition = {
  name: 'get_client_activity',
  description: 'Анализ активности клиента: заказы, счета и оплаты за период',
  inputSchema: {
    type: 'object',
    properties: {
      client_id: { type: 'string', description: 'ID клиента (обязательно)' },
      period_days: { type: 'number', description: 'Период анализа в днях (по умолчанию 30)' },
    },
    required: ['client_id'],
  },
  handler: async (params: Record<string, unknown>, context: { tenantId: string }) => {
    const result = await client.execute('get_client_activity', context.tenantId, params);
    if (!result.success) return `❌ ${result.error}`;

    const data = result.data as any;
    const counterpartyName = data.counterparty?.name || params.client_id;
    let msg = `*📈 Активность клиента: ${counterpartyName}*\n\n`;
    msg += `📦 Заказов: ${data.activity_summary?.total_orders || 0} на ${(data.activity_summary?.total_amount || 0).toLocaleString('ru-RU')} ₽\n`;
    msg += `🧾 Счетов: ${data.invoice_count || 0}\n`;
    msg += `💳 Оплат: ${data.payments?.length || 0} на ${(data.payment_total || 0).toLocaleString('ru-RU')} ₽\n`;
    msg += `📅 Последняя операция: ${data.last_activity_date || 'нет данных'}`;
    return msg;
  },
};

export default tool;
