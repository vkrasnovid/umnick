import { ToolsApiClient } from '../client.js';
import type { ToolDefinition } from '../types.js';

const client = new ToolsApiClient();

const tool: ToolDefinition = {
  name: 'get_overdue_payments',
  description: 'Просроченная дебиторская задолженность: показывает неоплаченные счета с истекшим сроком',
  inputSchema: {
    type: 'object',
    properties: {
      threshold_days: { type: 'number', description: 'Минимальная просрочка в днях (по умолчанию 0 — все просроченные)' },
      counterparty_id: { type: 'string', description: 'ID контрагента для фильтрации (опционально)' },
    },
  },
  handler: async (params: Record<string, unknown>, context: { tenantId: string }) => {
    const result = await client.execute('get_overdue_payments', context.tenantId, params);
    if (!result.success) return `❌ ${result.error}`;

    const data = result.data as any;
    if (!data?.overdue_invoices?.length) return '✅ Просроченной дебиторской задолженности нет.';

    const total = data.overdue_invoices.reduce((s: number, i: any) => s + (i.balance || i.amount || 0), 0);
    let msg = `*💰 Просроченная дебиторская задолженность*\n`;
    msg += `Сумма: *${total.toLocaleString('ru-RU')} ₽* | Счетов: ${data.overdue_invoices.length}\n\n`;
    
    data.overdue_invoices.slice(0, 10).forEach((inv: any) => {
      const days = inv.days_overdue || 0;
      const icon = days > 60 ? '🔴' : days > 30 ? '🟡' : '🟢';
      msg += `${icon} *${inv.counterparty || '—'}* — ${(inv.balance || inv.amount || 0).toLocaleString('ru-RU')} ₽ (${days} дн.)\n`;
    });

    if (data.overdue_invoices.length > 10) {
      msg += `\n_...и ещё ${data.overdue_invoices.length - 10} счетов_`;
    }
    return msg;
  },
};

export default tool;
