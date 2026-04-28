import { ToolsApiClient } from '../client.js';
import type { ToolDefinition } from '../types.js';

const client = new ToolsApiClient();

const tool: ToolDefinition = {
  name: 'list_active_clients',
  description: 'Список активных клиентов с фильтрацией по выручке и периоду активности, сортировка по убыванию выручки',
  inputSchema: {
    type: 'object',
    properties: {
      min_revenue: { type: 'number', description: 'Минимальная выручка для фильтрации (опционально)' },
      days: { type: 'number', description: 'Дни активности (по умолчанию 90)' },
      limit: { type: 'number', description: 'Максимальное количество результатов (по умолчанию 20)' },
    },
  },
  handler: async (params: Record<string, unknown>, context: { tenantId: string }) => {
    const result = await client.execute('list_active_clients', context.tenantId, params);
    if (!result.success) return `❌ ${result.error}`;

    const data = result.data as any;
    if (!data?.clients?.length) return '📭 Активных клиентов за указанный период не найдено.';

    let msg = `*🏪 Активные клиенты — Топ-${data.clients.length}*\n\n`;
    data.clients.forEach((c: any, i: number) => {
      const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '•';
      msg += `${medal} *${c.name || c.counterparty_name}* — ${(c.revenue || 0).toLocaleString('ru-RU')} ₽\n`;
    });
    return msg;
  },
};

export default tool;
