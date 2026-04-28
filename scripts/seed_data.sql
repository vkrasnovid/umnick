-- Seed data for development
-- Inserts demo tenant with sample data

-- Tenant
INSERT INTO umnick.tenants (id, name, inn, contact_email, odata_url, odata_db_name, subscription_tier)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'ООО "Ромашка"',
    '7701123456',
    'admin@romashka.ru',
    'https://demo-1c.umnick.ru/romashka/odata/standard.odata',
    'Бухгалтерия Предприятия',
    'pro'
);

-- Demo counterparties
INSERT INTO umnick.counterparties (id, tenant_id, external_id, name, inn, is_client, is_buyer, segment, status)
VALUES
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_CP_001', 'ИП Иванов', '7702123456', TRUE, TRUE, 'wholesale', 'active'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_CP_002', 'ООО "ТехноСервис"', '7703123456', TRUE, TRUE, 'vip', 'active'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a03', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_CP_003', 'ООО "СтройМаркет"', '7704123456', TRUE, TRUE, 'wholesale', 'active'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a04', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_CP_004', 'ИП Петрова', '7705123456', TRUE, FALSE, 'retail', 'active');

-- Demo contracts
INSERT INTO umnick.contracts (id, tenant_id, external_id, counterparty_id, number, date_start, date_end,
                              amount, currency, contract_type, status, utilization_sum, utilization_pct)
VALUES
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_CT_001', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01',
     'Д-2025/001', '2025-01-01', '2026-12-31',
     1500000, 'RUB', 'sales', 'active', 675000, 45.00),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_CT_002', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02',
     'Д-2025/002', '2025-03-01', '2026-12-31',
     3000000, 'RUB', 'sales', 'active', 1200000, 40.00),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a03', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_CT_003', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a03',
     'Д-2025/003', '2025-06-01', '2026-06-01',
     500000, 'RUB', 'purchase', 'active', 250000, 50.00);

-- Demo orders
INSERT INTO umnick.orders (id, tenant_id, external_id, counterparty_id, number, date, amount, status)
VALUES
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_ORD_001', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01',
     'ЗК-2026/042', '2026-04-15', 340000, 'confirmed'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_ORD_002', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02',
     'ЗК-2026/041', '2026-04-10', 210000, 'shipped'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a03', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_ORD_003', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a03',
     'ЗК-2026/040', '2026-04-05', 180000, 'completed'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a04', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_ORD_004', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01',
     'ЗК-2026/039', '2026-03-28', 89000, 'completed');

-- Demo invoices (with overdue)
INSERT INTO umnick.invoices (id, tenant_id, external_id, counterparty_id, order_id,
                             number, date, due_date, amount, paid_amount, status)
VALUES
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_INV_001', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01',
     'СФ-2026/015', '2026-03-25', '2026-04-10', 340000, 0, 'unpaid'),
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_INV_002', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a04',
     'СФ-2026/012', '2026-03-20', '2026-04-05', 89000, 45000, 'partial'),
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a03', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_INV_003', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02',
     'СФ-2026/011', '2026-03-15', '2026-04-01', 210000, 210000, 'paid'),
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a04', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_INV_004', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a04',
     'СФ-2026/010', '2026-03-01', '2026-04-15', 50000, 0, 'unpaid');

-- Demo products
INSERT INTO umnick.products (id, tenant_id, external_id, name, article, price, stock_balance,
                             stock_reserved, min_stock, category, unit)
VALUES
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_PR_001', 'Кирпич облицовочный М150', 'КР-001', 45, 0, 0, 500, 'Стройматериалы', 'шт'),
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_PR_002', 'Цемент М500 (50кг)', 'ЦМ-001', 350, 12, 0, 100, 'Стройматериалы', 'меш'),
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a03', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_PR_003', 'Арматура 12мм А500С', 'АР-001', 85, 0, 0, 5, 'Металлопрокат', 'т'),
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a04', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_PR_004', 'Песок строительный', 'ПС-001', 500, 3, 0, 10, 'Стройматериалы', 'м³'),
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a05', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'EXT_PR_005', 'Гвозди 100мм', 'ГВ-001', 0.50, 200, 0, 1000, 'Метизы', 'шт');

-- Demo watchers (starters)
INSERT INTO umnick.watchers (tenant_id, name, description, schedule, tool_name, tool_params,
                             condition, message_template, recipients, priority, enabled)
VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'daily_overdue_check',
     'Ежедневная проверка просроченных платежей в 9:00 по будням',
     '0 9 * * 1-5',
     'get_overdue_payments',
     '{"days_overdue_min": 1, "limit": 50, "threshold_amount": 1000}'::jsonb,
     'data.summary.total_overdue_count > 0',
     E'📋 *Ежедневный отчёт по просрочкам*\n\n'
     'Всего просроченных счетов: *{{data.summary.total_overdue_count}}*\n'
     'Общая сумма просрочки: *{{data.summary.total_overdue_sum | number}} {{data.summary.currency}}*',
     ARRAY['123456789'],
     'high',
     TRUE
    ),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'low_stock_alert',
     'Ежечасная проверка товаров с остатком ниже минимального',
     '0 * * * *',
     'list_active_clients',
     '{}'::jsonb,
     'True',
     E'⚠️ *Низкий остаток товаров*\n\nТребуется пополнение запасов.',
     ARRAY['123456789'],
     'normal',
     TRUE
    ),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
     'weekly_revenue_drop',
     'Еженедельная проверка: не упала ли выручка >20% по сравнению с прошлой неделей',
     '0 10 * * 1',
     'query_sales',
     '{"period_days": 14, "granularity": "week", "include_chart_data": true}'::jsonb,
     'data.chart_data and len(data.chart_data) >= 2',
     E'📊 *Мониторинг выручки*\n\nВыручка требует внимания.',
     ARRAY['123456789'],
     'normal',
     TRUE
    );
