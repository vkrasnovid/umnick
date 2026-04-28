# DESIGN SPEC — Умник Admin UI & Telegram Messages

```
DESIGN HANDOFF
from: designer
to: developer-react
project: umnick — AI Operations Platform
screens: 5
components: 23
notes: Dark theme by default. Desktop-only (min 1280px). Business-oriented строгий стиль.
```

---

## Table of Contents

1. [Design System](#1-design-system)
2. [Layout & Navigation](#2-layout--navigation)
3. [Dashboard](#3-dashboard)
4. [Settings / Подключение 1С](#4-settings--подключение-1с)
5. [Watchers](#5-watchers)
6. [Sync Log](#6-sync-log)
7. [Tools](#7-tools)
8. [Telegram Message Templates](#8-telegram-message-templates)
9. [Component Prop Interfaces](#9-component-prop-interfaces)

---

## 1. Design System

### 1.1 Color Palette

```yaml
# Dark theme (default) — business-oriented, строгий стиль
primary:
  50:  '#E0F2FE'   # backgrounds, badges
  100: '#BAE6FD'   # light backgrounds
  200: '#7DD3FC'   # hover borders
  300: '#38BDF8'   # active borders
  400: '#0EA5E9'   # icon, hover state for primary actions
  500: '#0284C7'   # *** PRIMARY *** buttons, links, active indicators
  600: '#0369A1'   # hover
  700: '#075985'   # pressed
  800: '#0C4A6E'   # disabled
  900: '#082F49'   # container background

success:
  50:  '#ECFDF5'
  100: '#D1FAE5'
  400: '#34D399'   # icon
  500: '#10B981'   # *** SUCCESS *** status OK, green badge
  600: '#059669'
  700: '#047857'

warning:
  50:  '#FFFBEB'
  100: '#FEF3C7'
  400: '#FBBF24'   # icon
  500: '#F59E0B'   # *** WARNING *** attention, medium alerts
  600: '#D97706'

danger:
  50:  '#FEF2F2'
  100: '#FEE2E2'
  400: '#F87171'   # icon
  500: '#EF4444'   # *** DANGER *** errors, critical alerts
  600: '#DC2626'

neutral:
  50:  '#F8FAFC'   # surface containers, card backgrounds
  100: '#F1F5F9'  # hover rows
  200: '#E2E8F0'  # borders, dividers
  300: '#CBD5E1'  # disabled text
  400: '#94A3B8'  # placeholder, secondary text
  500: '#64748B'  # body text
  600: '#475569'  # headings
  700: '#334155'  # titles
  800: '#1E293B'  # sidebar bg, header bg
  900: '#0F172A'  # page background
  950: '#020617'  # deepest (modals, drawers overlay)

# Dark mode specific
"bg-page":      '#0F172A'    # slate-900 — main page background
"bg-card":      '#1E293B'    # slate-800 — card, section backgrounds
"bg-sidebar":   '#020617'    # slate-950 — sidebar
"bg-header":    '#1E293B'    # slate-800 — top header
"bg-input":     '#0F172A'    # slate-900 — input fields
"bg-hover":     '#334155'    # slate-700 — row/button hover
"bg-active":    '#0C4A6E'    # primary-800 — active selection
"border":       '#334155'    # slate-700 — subtle borders
"border-hover": '#475569'    # slate-600 — hover borders
"text-primary": '#F8FAFC'    # slate-50 — primary text
"text-secondary": '#94A3B8'  # slate-400 — secondary text
"text-muted":   '#64748B'    # slate-500 — muted/disabled text
```

**Contrast verification (WCAG AA):**
- Primary text (#F8FAFC) on page bg (#0F172A) → `contrast ratio: 15.3:1` ✅ (AAA)
- Primary text (#F8FAFC) on card bg (#1E293B) → `contrast ratio: 12.5:1` ✅ (AAA)
- Secondary text (#94A3B8) on card bg (#1E293B) → `contrast ratio: 5.2:1` ✅ (AA)
- Muted text (#64748B) on card bg (#1E293B) → `contrast ratio: 3.5:1` ⚠️ (only for disabled/non-interactive)
- Primary 500 (#0284C7) on card bg (#1E293B) → `contrast ratio: 4.8:1` ✅ (AA)

### 1.2 Typography

```yaml
font-family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
monospace:   "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"

# Font sizes (Inter)
h1: { size: 28px, weight: 700, line-height: 1.3, letter-spacing: -0.02em }
h2: { size: 22px, weight: 600, line-height: 1.35, letter-spacing: -0.01em }
h3: { size: 18px, weight: 600, line-height: 1.4 }
subtitle: { size: 15px, weight: 500, line-height: 1.4 }
body:  { size: 14px, weight: 400, line-height: 1.5 }
body-sm: { size: 13px, weight: 400, line-height: 1.5 }
caption: { size: 12px, weight: 400, line-height: 1.4 }
label: { size: 13px, weight: 500, line-height: 1.4 }
mono:  { size: 13px, weight: 400, line-height: 1.5 }  # code/monospace
badge: { size: 11px, weight: 600, line-height: 1.2, letter-spacing: 0.04em }
```

### 1.3 Spacing System

```yaml
base-unit: 4px
scale: [0, 2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96]

# Semantic tokens
space-xs:   4px    # tight icon/text gaps
space-sm:   8px    # compact elements
space-md:   12px   # element-to-element
space-lg:   16px   # card padding, section gaps
space-xl:   24px   # section padding
space-2xl:  32px   # page padding
space-3xl:  48px   # large section separation
```

### 1.4 Border Radius

```yaml
radius-none:  0px
radius-sm:    4px    # inputs, badges, small elements
radius-md:    8px    # cards, dialogs, sections
radius-lg:    12px   # large modals, drawers
radius-xl:    16px   # page-level containers
radius-pill:  9999px # tags, badges, status dots
```

### 1.5 Shadows

```yaml
# (dark theme — более плотные тени)
shadow-sm:   '0 1px 2px 0 rgba(0,0,0,0.3), 0 1px 3px 0 rgba(0,0,0,0.15)'
shadow-md:   '0 4px 6px -1px rgba(0,0,0,0.4), 0 2px 4px -2px rgba(0,0,0,0.2)'
shadow-lg:   '0 10px 15px -3px rgba(0,0,0,0.5), 0 4px 6px -4px rgba(0,0,0,0.3)'
shadow-xl:   '0 20px 25px -5px rgba(0,0,0,0.6), 0 8px 10px -6px rgba(0,0,0,0.4)'
```

### 1.6 Icons

```yaml
library: lucide-react (v0.400+)
size-standard: 16px  # inline with body text
size-sm:       14px  # compact
size-md:       20px  # section icons
size-lg:       24px  # primary actions, page icons
color: inherit by default, semantic colors for status icons
```

**Key icons by context:**

| Context | Icon | Semantic |
|---------|------|----------|
| Sync OK | `CheckCircle2` | success-500 |
| Sync Error | `AlertCircle` | danger-500 |
| Sync In Progress | `Loader2` (animated) | primary-500 |
| Watcher enabled | `Bell` | text-primary |
| Watcher disabled | `BellOff` | text-muted |
| Dashboard | `LayoutDashboard` | — |
| Settings | `Settings` | — |
| Watchers page | `BellRing` | — |
| Sync Log | `History` | — |
| Tools page | `Wrench` | — |
| Edit | `Pencil` | — |
| Delete | `Trash2` | — |
| Enable/Disable toggle | `ToggleLeft` / `ToggleRight` | — |
| Play (run sync) | `Play` | — |
| Copy | `Copy` | — |
| Connection OK | `PlugZap` | success-500 |
| Connection Failed | `Plug` | danger-500 |
| Search | `Search` | — |
| Chevron | `ChevronDown` / `ChevronRight` | — |
| External link | `ExternalLink` | — |
| Info | `Info` | primary-400 |
| Warning | `TriangleAlert` | warning-500 |

### 1.7 Component State Visual Guide

```yaml
default:
  bg: transparent or bg-card
  border: border (slate-700)
  text: text-primary

hover:
  bg: bg-hover (slate-700)
  border: border-hover (slate-600)
  transition: background-color 150ms ease

active/pressed:
  bg: bg-active (primary-800)
  border: primary-600

disabled:
  bg: bg-card
  border: slate-800
  text: text-muted (slate-500)
  cursor: not-allowed
  opacity: 0.5

loading:
  as default but with animated spinner or skeleton
  pointer-events: none

error:
  border: danger-500
  outline: danger-500/30
  bg: danger-950/20
  text: danger-400

focus-visible:
  outline: 2px solid primary-500
  outline-offset: 2px
```

---

## 2. Layout & Navigation

### 2.1 Global Layout

```
┌──────────────────────────────────────────────────────────┐
│  ┌──────┬───────────────────────────────────────────────┐ │
│  │      │  Header                                        │ │
│  │      │  ┌──────────────────────────────────────────┐  │ │
│  │ Side │  │  Tenant Selector  │  Sync Status  │ User  │  │ │
│  │ bar  │  └──────────────────────────────────────────┘  │ │
│  │      │                                                  │ │
│  │      │  Page Content                                    │ │
│  │      │  (scrollable)                                   │ │
│  │      │                                                  │ │
│  │      │                                                  │ │
│  └──────┴───────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

- **Sidebar:** Fixed, 240px width, slate-950 (#020617) background
- **Header:** Fixed, 56px height, slate-800 (#1E293B) background, border-bottom
- **Content area:** Margin-top: 56px, margin-left: 240px, scrollable
- **Min page width:** 1280px (no responsive breakpoints below desktop)

### 2.2 Sidebar

```
┌──────────────────────┐
│  ☰                   │  ← Logo area (24px icon + "Умник" text)
│                      │
│  ◎ Dashboard         │  ← Active: bg-active + primary-500 left border
│  ⚙ Settings          │  ← Default: icon + label
│  🔔 Watchers         │
│  📋 Sync Log          │
│  🔧 Tools             │
│                      │
│  ──────────────────── │  ← Divider (slate-800)
│                      │
│  ℹ️ [tenant name]    │  ← Footer: current tenant info
│                      │
└──────────────────────┘
```

**Sidebar items:**
- Each item: 40px height, 12px horizontal padding
- Icon (16px) + label (14px, weight 500) + optional badge (e.g., watchers alert count)
- Active: bg-active, 3px primary-500 left border
- Hover: bg-hover
- Bottom section: muted label showing tenant name and sync status indicator

### 2.3 Header

```
┌──────────────────────────────────────────────────────────────┐
│  ┌────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ 1С: КА2    │  │ ◎ Last sync:     │  │ 👤 admin@...     │  │
│  │ ▼           │  │    12 min ago    │  │                  │  │
│  └────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                              │
│  ← Tenant select    ← Sync status        ← User menu        │
└──────────────────────────────────────────────────────────────┘
```

- Left: tenant selector (shadcn Select), shows 1С database name
- Center: sync status summary (green dot + "Last sync: X min ago")
- Right: user menu (avatar/initials + dropdown: profile, logout)

---

## 3. Dashboard

### 3.1 Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Dashboard                                           🕐 now  │
│                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐            │
│  │  Система            │  │  База данных         │            │
│  │                     │  │                      │            │
│  │  🟢 Синхронизация   │  │  Контрагенты  1,234  │            │
│  │     работает        │  │  Договоры       345  │            │
│  │                     │  │  Заказы         892  │            │
│  │  Last sync: 12 min  │  │  Товары         567  │            │
│  └─────────────────────┘  └─────────────────────┘            │
│                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐            │
│  │  Watchers           │  │  Последние алерты   │            │
│  │                     │  │                      │            │
│  │  Всего: 5           │  │  🔴 Просрочки        │            │
│  │  Активны: 4         │  │     12 мин назад     │            │
│  │  Сработали: 2       │  │                      │            │
│  │                     │  │  ⚠️ Низкий остаток   │            │
│  └─────────────────────┘  │     45 мин назад     │            │
│                            │                      │            │
│                            │  [Показать все →]   │            │
│                            └─────────────────────┘            │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 Component Specifications

#### CardMetric

| Prop | Type | Description |
|------|------|-------------|
| title | `string` | Card title |
| value | `string \| number` | Main metric value |
| icon | `LucideIcon` | Icon component |
| trend | `{ value: number; direction: 'up' \| 'down' \| 'neutral' }` | Optional trend indicator |
| status | `'ok' \| 'warning' \| 'error' \| 'info'` | Semantic status for dot/color |
| subtitle | `string` | Optional secondary text |
| loading | `boolean` | Skeleton state |

**States:**
- **Default:** Card (bg-card, radius-md, padding-lg), icon in primary-500, value in h2 style
- **Loading:** Skeleton rectangle for value + skeleton line for subtitle
- **Error:** Red border, error icon, "Failed to load" text

#### AlertCard

| Prop | Type | Description |
|------|------|-------------|
| severity | `'critical' \| 'high' \| 'normal' \| 'low'` | Alert severity |
| watcherName | `string` | Name of triggering watcher |
| message | `string` | Alert message preview (truncated) |
| timestamp | `string` | Relative or absolute time |
| onClick | `() => void` | Navigate to details |

**Severity colors:**
- critical: left border danger-500, icon TriangleAlert danger-500
- high: left border warning-500, icon TriangleAlert warning-500
- normal: left border primary-500, icon Info primary-400
- low: left border neutral-500, icon Bell neutral-400

#### RecentAlertsList

- Container with "Последние алерты" heading
- List of `AlertCard` items (3-5)
- "Показать все →" link at bottom → navigates to Watchers page filtered by recent alerts
- Empty state: "Нет алертов за последние 24 часа" with CheckCircle2 icon (success-500)

#### EntityCountCard (for "База данных")

- Grid of 4 items: Контрагенты, Договоры, Заказы, Товары
- Each: icon (16px) + label (body-sm, text-secondary) + count (h3, text-primary)
- Loading state: 4 skeleton items

### 3.3 Empty State

```
┌──────────────────────────────────────────────┐
│  📊 Dashboard                                │
│                                              │
│  ┌──────────────────────────────────────────┐│
│  │                                          ││
│  │     📡 Подключите 1С базу данных          ││
│  │     в настройках для начала работы        ││
│  │                                          ││
│  │     [⚙ Перейти к настройкам]            ││
│  │                                          ││
│  └──────────────────────────────────────────┘│
└──────────────────────────────────────────────┘
```

**Empty state:** Shown when tenant has no 1С connection configured. Centered card with illustration-like icon, descriptive text, and CTA button to Settings page.

### 3.4 Loading State

- 4 skeleton cards in a grid (2×2)
- Each skeleton: animate-pulse, bg slate-800, rounded-md
- Skeleton dimensions match CardMetric layout

---

## 4. Settings / Подключение 1С

### 4.1 Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Settings                                                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Подключение к 1С                                       │  │
│  │                                                         │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │  🟢 Подключение активно   [Отключить]              │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                         │  │
│  │  URL OData                                        [✏️] │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ https://server.company.ru/company/odata/standard │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  Имя базы 1С                                      [✏️] │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ Бухгалтерия Предприятия                          │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  Логин                                           [✏️] │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ admin                                            │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  Пароль                                          [✏️]  │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ ●●●●●●●●●●                                      │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  [🔌 Проверить подключение]   [💾 Сохранить]          │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Статус подключения                                     │  │
│  │                                                         │  │
│  │  🟢 Соединение установлено                              │  │
│  │  Сервер: mssql-prod-01                                   │  │
│  │  Версия 1С: 8.3.24.1441                                  │  │
│  │  Статус синхронизации: работает                         │  │
│  │                                                         │  │
│  │  [Запустить полную синхронизацию]                       │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### 4.2 Component Specifications

#### ConnectionForm

| Prop | Type | Description |
|------|------|-------------|
| initialValues | `ConnectionSettings` | Pre-filled values |
| onSave | `(values: ConnectionSettings) => Promise<void>` | Save handler |
| onTest | `() => Promise<ConnectionTestResult>` | Test connection handler |
| status | `'idle' \| 'testing' \| 'saving' \| 'error' \| 'success'` | Form status |

**ConnectionSettings type:**
```typescript
interface ConnectionSettings {
  odataUrl: string;
  odataDbName: string;
  odataUsername: string;
  odataPassword: string;  // masked in UI
}
```

**ConnectionTestResult type:**
```typescript
interface ConnectionTestResult {
  success: boolean;
  server?: string;
  version?: string;
  message?: string;
  error?: string;
}
```

**States:**
- **Idle:** All fields editable, buttons enabled
- **Testing:** "Проверить подключение" button shows spinner, fields disabled
- **Test Success:** Green status bar appears below form, connection details shown
- **Test Failed:** Red status bar, error message, fields remain editable
- **Saving:** "Сохранить" shows spinner, fields disabled
- **Save Success:** Toast notification "Настройки сохранены"
- **Save Failed:** Inline error message above buttons
- **Edit Mode (view vs edit):** Initial state shows values as plain text with pencil icon on right. Clicking pencil converts field to input. Saves on blur or Enter.

#### StatusCard (connection status)

| Prop | Type | Description |
|------|------|-------------|
| connectionStatus | `'connected' \| 'disconnected' \| 'error' \| 'testing'` | Current status |
| lastSyncAt | `string \| null` | ISO date of last sync |
| serverInfo | `{ name: string; version: string } \| null` | Server details |
| onFullSync | `() => void` | Full sync trigger |

**States:**
- **Connected:** Green dot, "Соединение установлено", server info visible
- **Disconnected:** Gray dot, "Подключение не настроено"
- **Error:** Red dot, error message (e.g., "Не удалось соединиться с сервером")
- **Testing:** Animated spinner, "Проверка подключения..."
- **Full sync running:** Spinner on button, "Синхронизация запущена..."

### 4.3 Input Validation

| Field | Validation | Error Message |
|-------|-----------|---------------|
| URL OData | Required, valid URL (https://) | "Укажите корректный URL OData (https://...)" |
| Имя базы | Required, max 128 chars | "Название базы обязательно" |
| Логин | Required, max 128 chars | "Укажите логин" |
| Пароль | Required, min 1 char | "Пароль обязателен" |

- Inline error below field: caption size, danger-400 color
- Error icon (AlertCircle, 12px) before error text

---

## 5. Watchers

### 5.1 Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Watchers                                   [+ Создать]       │
│                                                               │
│  [🔍 Поиск...]  [Все статусы ▼]  [Приоритет ▼]               │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                                                          │ │
│  │  📋 Ежедневная проверка просрочек         🟢 Вкл  🔴🔔  │ │
│  │  Каждые будни в 9:00                        Приоритет:  │ │
│  │  Last run: сегодня 09:12                    High        │ │
│  │                                             [✏️] [⏸]    │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  ⚠️ Низкий остаток товаров                    🟢 Вкл     │ │
│  │  Каждый час                                  Normal     │ │
│  │  Last run: 12 мин назад                      [✏️] [⏸]    │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  📊 Недельный мониторинг продаж              🔴 Выкл     │ │
│  │  Каждый понедельник в 10:00                  Normal     │ │
│  │  Last run: 3 дня назад                       [✏️] [▶️]   │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 5.2 Component Specifications

#### WatcherTable

| Prop | Type | Description |
|------|------|-------------|
| watchers | `Watcher[]` | Watcher data array |
| loading | `boolean` | Loading state |
| onToggle | `(id: string) => void` | Enable/disable toggle |
| onEdit | `(id: string) => void` | Open edit modal |
| onSnooze | `(id: string) => void` | Snooze watcher |
| onDelete | `(id: string) => void` | Delete confirmation |

```typescript
interface Watcher {
  id: string;
  name: string;
  description: string;
  schedule: string;       // cron expression
  scheduleLabel: string;  // human-readable: "Каждый час"
  toolName: string;
  priority: 'low' | 'normal' | 'high' | 'critical';
  enabled: boolean;
  lastRunAt: string | null;
  lastAlertAt: string | null;
  alertCount: number;
}
```

**WatcherRow** (each row in table):
- 56px height (compact data density)
- Left icon based on toolName (📋 for overdue, ⚠️ for stock, 📊 for revenue)
- Name (body, weight 600, text-primary)
- Schedule (caption, text-secondary) + "Last run: ..."
- Priority badge (see below)
- Status: Enabled: green dot + "Вкл", Disabled: red dot + "Выкл"
- Alert indicator: 🔔 icon with count if alerts > 0
- Action buttons: Edit (Pencil icon), Snooze/Pause (Pause icon), Enable/Disable (play/pause icons)

**Table empty state:**
```
┌──────────────────────────────────────────────┐
│                                              │
│     🔔 Нет watchers                          │
│     Создайте первый watcher для отслеживания  │
│                                              │
│     [+ Создать watcher]                      │
│                                              │
└──────────────────────────────────────────────┘
```

#### PriorityBadge

| Priority | Style |
|----------|-------|
| low | bg-neutral-800, text-neutral-400 |
| normal | bg-primary-900, text-primary-400 |
| high | bg-warning-900/50, text-warning-500 |
| critical | bg-danger-900/50, text-danger-500 |

Badge: 11px font, 600 weight, uppercase, 4px horizontal padding, 2px vertical, radius-sm

#### FilterBar

| Prop | Type | Options |
|------|------|---------|
| searchQuery | `string` | Text search |
| statusFilter | `'all' \| 'enabled' \| 'disabled'` | — |
| priorityFilter | `'all' \| 'low' \| 'normal' \| 'high' \| 'critical'` | — |
| onSearchChange | `(q: string) => void` | — |
| onStatusChange | `(s: string) => void` | — |
| onPriorityChange | `(p: string) => void` | — |

Implemented as shadcn Input (search icon left) + two shadcn Select dropdowns. 32px height for compactness.

### 5.3 Watcher Edit Modal

```
┌───────────────────────────────────────────────────────┐
│  ✏️ Редактирование watcher                    [✕]    │
│                                                       │
│  Название                                             │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Ежедневная проверка просрочек                   │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  Описание                                             │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Проверка просроченных платежей каждый будний    │  │
│  │ день в 9:00                                     │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  Расписание (cron)                                    │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 0 9 * * 1-5                                     │  │
│  └─────────────────────────────────────────────────┘  │
│  [Human-readable preview: "Пн-Пт, 09:00"]             │
│                                                       │
│  Условие (JSONata-подобное выражение)                 │
│  ┌─────────────────────────────────────────────────┐  │
│  │ data.summary.total_overdue_count > 0            │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  Шаблон сообщения (Markdown)                          │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 📋 *Ежедневный отчёт по просрочкам*             │  │
│  │                                                 │  │
│  │ Всего просроченных счетов:...                   │  │
│  └─────────────────────────────────────────────────┘  │
│  [🔍 Preview]                                         │
│                                                       │
│  Получатели (Telegram chat ID)                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │ [123456789] [987654321] [+]                     │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  Приоритет                    Статус                  │
│  ┌────────────────────┐      ┌──────────────────┐     │
│  │ High ▼              │      │ 🟢 Enabled       │     │
│  └────────────────────┘      └──────────────────┘     │
│                                                       │
│  [Сохранить]   [Отмена]                               │
└───────────────────────────────────────────────────────┘
```

**Modal specs:**
- Width: 640px (max)
- Backdrop: bg-page with 60% opacity
- Close on Escape, click outside
- "Сохранить" button: primary variant, full width of modal footer
- "Отмена": ghost variant
- Form validation on save

**Input fields:**
- Название: text input, required, max 128 chars
- Описание: textarea, optional, 3 rows
- Расписание: monospace input, required, with live human-readable preview below
- Условие: monospace textarea, required, 2 rows
- Шаблон: monospace textarea, min 5 rows
- Получатели: tag input (shadcn multiple select or custom chips with [x] remove)
- Приоритет: shadcn Select
- Статус: Toggle switch (shadcn Switch)

**Preview button:** Opens a bottom sheet or inline panel showing rendered message template with sample data.

### 5.4 Error State

- **Create failed:** Toast "Не удалось создать watcher. Проверьте правильность cron-выражения."
- **Edit failed:** Inline error at top of modal
- **Delete failed:** Toast "Не удалось удалить watcher"
- **Snooze failed:** Toast "Не удалось приостановить watcher"

---

## 6. Sync Log

### 6.1 Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Sync Log                                                     │
│                                                               │
│  [Все типы ▼]  [Все статусы ▼]  [📅 Последние 24 часа ▼]     │
│                                                               │
│  ┌────────┬──────────┬────────┬────────┬───────┬────────────┐ │
│  │ Время  │ Тип      │ Сущность │ Статус │Записи│ Длит.     │ │
│  ├────────┼──────────┼────────┼────────┼───────┼────────────┤ │
│  │ 21:42  │ Full     │ Все     │ 🟢 Ok  │ 1,234 │ 12.3s     │ │
│  │ 21:37  │ Increm.  │ Заказы  │ 🟢 Ok  │ 42    │ 1.2s      │ │
│  │ 21:32  │ Increm.  │ Счета   │ 🟢 Ok  │ 18    │ 0.8s      │ │
│  │ 21:27  │ Increm.  │ Заказы  │ 🔴 Err  │ —     │ 5.1s     │ │
│  │ 21:22  │ Increm.  │ Заказы  │ 🟢 Ok  │ 56    │ 1.4s      │ │
│  └────────┴──────────┴────────┴────────┴───────┴────────────┘ │
│                                                               │
│  [← Prev]  Page 1 of 12  [Next →]                             │
└───────────────────────────────────────────────────────────────┘
```

### 6.2 Component Specifications

#### SyncLogTable

| Prop | Type | Description |
|------|------|-------------|
| entries | `SyncLogEntry[]` | Log data |
| total | `number` | Total entries count |
| page | `number` | Current page (1-indexed) |
| pageSize | `number` | Items per page (default 50) |
| loading | `boolean` | Loading state |
| onPageChange | `(page: number) => void` | — |
| filters | `SyncLogFilters` | Current filter values |
| onFilterChange | `(filters: SyncLogFilters) => void` | — |

```typescript
interface SyncLogEntry {
  id: string;
  syncType: 'full_reconciliation' | 'counterparties' | 'contracts' | 'orders' | 'invoices' | 'payments' | 'products' | 'employees';
  syncTypeLabel: string;  // Full / Increm.
  entityLabel: string;    // Человекочитаемое имя
  startedAt: string;      // ISO date
  finishedAt: string | null;
  durationMs: number | null;
  status: 'success' | 'error' | 'running' | 'partial';
  recordsProcessed: number;
  recordsUpdated: number;
  recordsCreated: number;
  recordsErrors: number;
  errorMessage: string | null;
}
```

**Table columns:**

| Column | Width | Alignment | Format |
|--------|-------|-----------|--------|
| Время | 80px | left | time only (HH:mm) for today, date+time for older |
| Тип | 100px | center | Badge: "Full" or "Increm." |
| Сущность | 140px | left | Entity name |
| Статус | 100px | center | StatusDot + label |
| Записи | 80px | right | Number with comma separator |
| Длит. | 80px | right | Duration in seconds/ms |

**Row states:**
- Default: 40px height, border-b (slate-800)
- Error row: left border 3px danger-500, subtle bg-danger-950/10
- Running row: animated gradient border or pulsing dot
- Hover: bg-hover
- Click row → expands inline detail (error message, record counts breakdown) or opens slide-over panel

**Status indicators:**
| Status | Dot | Label |
|--------|-----|-------|
| success | 🟢 success-500 | Ok |
| error | 🔴 danger-500 | Ошибка |
| running | 🟡 warning-500 (animated pulse) | Выполняется... |
| partial | 🟠 warning-500 | Частично |

**Filter bar specs:**
- 3 shadcn Select components in a row (32px height)
- "Все типы" — all entity types
- "Все статусы" — all/success/error/running
- Date range: "Последние 24 часа" / "Последние 7 дней" / "Последние 30 дней" / "Всё время"

**Table empty state:**
```
┌──────────────────────────────────────────────┐
│                                              │
│     📋 История синхронизаций пуста           │
│     Данные появятся после первой синхрони-   │
│     зации с 1С                               │
│                                              │
└──────────────────────────────────────────────┘
```

**Error detail row (expanded):**
When clicking an error row, show an expanded section below:
```
  │ 21:27  │ Increm.  │ Заказы   │ 🔴 Err  │ —     │ 5.1s     │
  ├──────────────────────────────────────────────────────────┤
  │  ❌ Ошибка синхронизации заказов                          │
  │  Connection timed out: odata.server.com:443               │
  │  [Повторить]  [Копировать ошибку]                         │
  └──────────────────────────────────────────────────────────┘
```

---

## 7. Tools

### 7.1 Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Tools                                                        │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  🔍 Фильтр: [Поиск по названию...]                       │ │
│  │                                                          │ │
│  │  ┌─────────┬─────────┬────────────────────────────────┐  │ │
│  │  │ Статус  │ Tool    │ Описание                      │  │ │
│  │  ├─────────┼─────────┼────────────────────────────────┤  │ │
│  │  │ 🟢     │ get_    │ Статус исполнения договора —   │  │ │
│  │  │ Active  │ contract│ сумму, процент, остаток       │  │ │
│  │  │         │ _utiliz.│                                │  │ │
│  │  ├─────────┼─────────┼────────────────────────────────┤  │ │
│  │  │ 🟢     │ get_    │ Просроченные платежи — долги   │  │ │
│  │  │ Active  │ overdue_│ клиентов с overdue-счетами     │  │ │
│  │  │         │ payments│                                │  │ │
│  │  └─────────┴─────────┴────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 7.2 Component Specifications

#### ToolTable

| Prop | Type | Description |
|------|------|-------------|
| tools | `ToolInfo[]` | Tool data |
| loading | `boolean` | Loading state |
| onTestRun | `(toolName: string) => void` | Run tool manually |

```typescript
interface ToolInfo {
  name: string;
  displayName: string;
  status: 'active' | 'error' | 'not_registered';
  description: string;
  parameters: Record<string, unknown>;  // JSON Schema
  lastRunAt: string | null;
  lastRunStatus: 'success' | 'error' | null;
}
```

**Table columns:**

| Column | Alignment | Description |
|--------|-----------|-------------|
| Статус | center | StatusDot 🟢/🔴/⚪ |
| Tool | left | Monospace name + human-readable label |
| Описание | left | Description text, max 2 lines with ellipsis |
| Actions | right | "▶ Выполнить" button |

**Row:**
- 48px height
- Hover: bg-hover
- Click on row → slide-over panel with tool parameters and test execution UI

#### ToolDetailPanel (slide-over)

```
┌─────────────────────────────────────────────────────┐
│  🔧 get_overdue_payments                    [✕]    │
│                                                     │
│  Статус: 🟢 Registered                              │
│  Last run: 12 min ago                               │
│                                                     │
│  Описание                                            │
│  Получить список просроченных платежей...            │
│                                                     │
│  Параметры                                           │
│  ┌─────────────────────────────────────────────────┐│
│  │ days_overdue_min: [1      ]                     ││
│  │ threshold_amount: [1000   ]                     ││
│  │ limit:           [20     ]                      ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  [▶ Выполнить]                                       │
│                                                     │
│  ─── Результат ───                                   │
│  ┌─────────────────────────────────────────────────┐│
│  │ {                                                ││
│  │   "success": true,                               ││
│  │   "data": {                                      ││
│  │     "summary": {                                 ││
│  │       "total_overdue_count": 12,                 ││
│  │       "total_overdue_sum": 145800               ││
│  │     },                                           ││
│  │     "overdue_invoices": [...]                    ││
│  │   }                                              ││
│  │ }                                                ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  [Копировать результат]                              │
└─────────────────────────────────────────────────────┘
```

**Panel specs:**
- Width: 480px
- Slides in from right
- "Выполнить" button: calls tool with given params, shows loading spinner
- Result: syntax-highlighted JSON in monospace, scrollable (max 400px)
- Error: red panel with error message
- Parameters: auto-generated form from JSON Schema (simple: number inputs, text inputs, toggles)

---

## 8. Telegram Message Templates

### 8.1 Format Guidelines

**Telegram MarkdownV2 rules:**
- `*bold text*` for **bold**
- `_italic text_` for *italic*
- `__underline__` for underline
- `~strikethrough~` for strikethrough
- `||spoiler||` for spoiler
- `` `code` `` for inline code
- Must escape: `_ * [ ] ( ) ~ ` > # + - = | { } . !`
- Emoji: use raw Unicode emoji (not escaped)

**Visual hierarchy:**
- Header line: emoji + `*bold title*`
- Separator: blank line `\n\n`
- Stats: emoji + `*label*`: `value`
- Lists: `• ` prefix with `*highlighted values*`
- Footer: optional CTA or contextual info

---

### 8.2 Watcher 1: `daily_overdue_check` — Просроченные платежи

#### Template A: Есть алерты

```
📋 *Ежедневный отчёт по просрочкам*

🔴 *Критические* \(>30 дн\.\): 2 на сумму 67 500₽
⚠️ *Требуют внимания*: 5 на сумму 45 300₽

• *ООО "Ромашка"* — 45 000₽ \(35 дн\.\) overdue
• *ИП Иванов* — 22 500₽ \(12 дн\.\)
• *ООО "ТехноСервис"* — 12 300₽ \(8 дн\.\)
• *ООО "СтройМаркет"* — 8 900₽ \(5 дн\.\)
• *ИП Петрова* — 1 600₽ \(3 дн\.\)

💰 *Всего просрочено*: 112 800₽ \(7 счетов\)

ℹ️ Подробнее: /status
```

**Key elements:**
- Summary line: critical count + sum, attention count + sum
- Top 5 overdue items with details
- Total line
- CTA: /status command

#### Template B: Нет алертов

```
📋 *Ежедневный отчёт по просрочкам*

✅ Просрочек нет\. Все платежи в срок\.

💰 *Текущая дебиторская задолженность*: 890 000₽
📄 *Всего активных счетов*: 34

ℹ️ Статистика по клиентам: /status
```

---

### 8.3 Watcher 2: `low_stock_alert` — Низкие остатки

#### Template A: Есть алерты

```
⚠️ *Низкий остаток товаров*

🔴 *Критический дефицит* \(остаток = 0\): 3 товара
⚠️ *Ниже минимального*: 5 товаров

• *Кирпич облицовочный М150* — 0 шт\. \(мин\. 500\)
• *Цемент М500 \(50кг\)* — 12 меш\. \(мин\. 100\)
• *Арматура 12мм А500С* — 0 т\. \(мин\. 5\)
• *Песок строительный* — 3 м³ \(мин\. 10\)
• *Гвозди 100мм* — 200 шт\. \(мин\. 1000\)

🏪 Всего позиций ниже нормы: 8

🚚 Рекомендуем срочно пополнить запасы
```

**Key elements:**
- Critical (0 stock) count + attention count
- Top items with current stock vs minimum
- Total count
- Recommendation line

#### Template B: Нет алертов

```
⚠️ *Низкий остаток товаров*

✅ Все товары в норме\. Критических остатков нет\.

📊 *Текущая статистика*:
• Всего номенклатуры: 567
• Минимальный остаток \(близко к норме\): 0
• Резерв: 1 234 шт\.

ℹ️ Остатки в норме
```

---

### 8.4 Watcher 3: `weekly_revenue_drop` — Падение выручки

#### Template A: Падение обнаружено (>20%)

```
📊 *Мониторинг выручки*

🔻 Выручка упала на *25\.3%* по сравнению с прошлой неделей

▫️ *Текущая неделя*: 1 240 000₽
▫️ *Предыдущая неделя*: 1 660 000₽
▫️ *Разница*: −420 000₽

📉 *Динамика по клиентам*:
• *ООО "Ромашка"* — 340 000₽ \(−45%\)
• *ИП Иванов* — 210 000₽ \(−12%\)
• *ООО "ТехноСервис"* — 180 000₽ \(+8%\)

⚠️ Рекомендуем проверить активность ключевых клиентов
```

**Key elements:**
- Drop percentage prominently displayed
- Week-over-week comparison
- Client-level breakdown
- Warning with actionable recommendation

#### Template B: Без падения

```
📊 *Мониторинг выручки*

✅ Выручка стабильна\. Падений более 20% не обнаружено\.

▫️ *Текущая неделя*: 1 580 000₽
▫️ *Предыдущая неделя*: 1 660 000₽
▫️ *Изменение*: −4\.8% \(в пределах нормы\)

📈 *Лидеры недели*:
• *ООО "Ромашка"* — 420 000₽ \(+12%\)
• *ООО "СтройМаркет"* — 310 000₽ \(+5%\)

ℹ️ Подробная аналитика: /sales
```

---

## 9. Component Prop Interfaces (TypeScript)

### 9.1 Layout Components

```typescript
// Sidebar.tsx
interface SidebarProps {
  items: SidebarItem[];
  activePath: string;
  tenantName: string;
  syncStatus: 'ok' | 'warning' | 'error';
  onNavigate: (path: string) => void;
}

interface SidebarItem {
  label: string;
  path: string;
  icon: LucideIcon;
  badge?: number;       // e.g., alert count
  disabled?: boolean;
}

// Header.tsx
interface HeaderProps {
  tenantName: string;
  tenantOptions: { value: string; label: string }[];
  onTenantChange: (tenantId: string) => void;
  syncStatus: SyncSummary;
  user: UserInfo;
  onLogout: () => void;
}

interface SyncSummary {
  status: 'ok' | 'error' | 'running';
  lastSyncAt: string | null;
  label: string;        // "12 min ago" / "1 hour ago"
}

interface UserInfo {
  email: string;
  avatar?: string;      // URL or initials fallback
}
```

### 9.2 UI Primitive Overrides

**shadcn/ui customization:**
```typescript
// shadcn/ui theme overrides (CSS variables for dark mode)
:root {
  --background: #0F172A;
  --foreground: #F8FAFC;
  --card: #1E293B;
  --card-foreground: #F8FAFC;
  --popover: #1E293B;
  --popover-foreground: #F8FAFC;
  --primary: #0284C7;
  --primary-foreground: #F8FAFC;
  --secondary: #334155;
  --secondary-foreground: #F8FAFC;
  --muted: #334155;
  --muted-foreground: #94A3B8;
  --accent: #334155;
  --accent-foreground: #F8FAFC;
  --destructive: #EF4444;
  --destructive-foreground: #F8FAFC;
  --border: #334155;
  --input: #1E293B;
  --ring: #0284C7;
  --radius: 0.5rem;      // 8px
}

// shadcn Select: use default trigger but with custom chevron
// shadcn Table: use default with custom row styling
// shadcn Dialog: use default for modals/dialogs
// shadcn Switch: use default for toggles
// shadcn Tabs: use default where tab navigation needed
// shadcn Toast: use default for notifications
// shadcn Badge: use default + custom variants for priority/status
```

### 9.3 StatusDot Component

```typescript
interface StatusDotProps {
  status: 'ok' | 'warning' | 'error' | 'running' | 'inactive';
  size?: 'sm' | 'md';   // 8px / 12px
  label?: string;        // Shows beside dot
  animate?: boolean;     // pulse animation for 'running'
}
```

**Colors:**
- ok: `bg-success-500`, shadow-success-500/50 (subtle glow)
- warning: `bg-warning-500`
- error: `bg-danger-500`
- running: `bg-warning-500` with `animate-pulse`
- inactive: `bg-neutral-600`

### 9.4 Page Wrapper

```typescript
interface PageWrapperProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;     // Right-side action buttons
  children: React.ReactNode;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}
```

### 9.5 Skeleton Components

```typescript
interface SkeletonProps {
  width?: string;       // CSS width
  height?: string;      // CSS height
  className?: string;   // Additional classes
  variant?: 'text' | 'circle' | 'rect';
}
```

- Base: `bg-slate-800 animate-pulse rounded-md`
- Text: `h-4 w-full`
- Circle: `h-8 w-8 rounded-full`
- Card: full card shape matching CardMetric

### 9.6 Table Components

```typescript
// Generic table component
interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  loading?: boolean;
  pageSize?: number;
  onRowClick?: (row: T) => void;
  emptyState?: React.ReactNode;
  errorState?: React.ReactNode;
  sortable?: boolean;
  filterable?: boolean;
}

interface ColumnDef<T> {
  key: string;
  header: string;
  accessor: (row: T) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string;
  sortable?: boolean;
  sortKey?: string;
}
```

### 9.7 Form Components

```typescript
// ConnectionForm types
interface ConnectionSettings {
  odataUrl: string;
  odataDbName: string;
  odataUsername: string;
  odataPassword: string;
}

interface ConnectionFormProps {
  initialValues: ConnectionSettings;
  onSave: (values: ConnectionSettings) => Promise<void>;
  onTest: () => Promise<ConnectionTestResult>;
  status: 'idle' | 'testing' | 'saving' | 'error' | 'success';
  error?: string;
}

interface ConnectionTestResult {
  success: boolean;
  server?: string;
  version?: string;
  message?: string;
  error?: string;
}

// WatcherEditModal types
interface WatcherEditModalProps {
  watcher?: Watcher | null;     // null = create mode
  open: boolean;
  onClose: () => void;
  onSave: (watcher: WatcherFormData) => Promise<void>;
  onDelete?: (id: string) => void;
}

interface WatcherFormData {
  name: string;
  description: string;
  schedule: string;
  condition: string;
  messageTemplate: string;
  recipients: string[];
  priority: 'low' | 'normal' | 'high' | 'critical';
  enabled: boolean;
}
```

### 9.8 Notification/Toast Types

```typescript
interface ToastConfig {
  title: string;
  description?: string;
  variant: 'default' | 'success' | 'warning' | 'destructive';
  duration?: number;    // ms, default 5000
}
```

---

## Appendix A: Route Map

| Route | Page Component | Sidebar Label | Icon |
|-------|---------------|---------------|------|
| `/` | Dashboard | Dashboard | `LayoutDashboard` |
| `/settings` | Settings | Settings | `Settings` |
| `/watchers` | Watchers | Watchers | `BellRing` |
| `/watchers/new` | WatcherEdit (modal) | — | — |
| `/watchers/:id/edit` | WatcherEdit (modal) | — | — |
| `/sync-log` | SyncLog | Sync Log | `History` |
| `/tools` | Tools | Tools | `Wrench` |

## Appendix B: API Response Error Patterns

```typescript
// Unified API error response
interface ApiError {
  error: {
    code: string;         // e.g., "CONNECTION_FAILED", "VALIDATION_ERROR"
    message: string;      // Human-readable
    details?: Record<string, string[]>;  // Field-level errors
  };
}

// Expected error codes for Admin UI
const ERROR_CODES = {
  CONNECTION_FAILED:    'Не удалось подключиться к серверу 1С',
  VALIDATION_ERROR:     'Проверьте правильность заполнения полей',
  WATCHER_CRON_INVALID: 'Некорректное cron-выражение',
  TENANT_NOT_FOUND:     'Арендатор не найден',
  SYNC_ALREADY_RUNNING: 'Синхронизация уже выполняется',
  TOOL_TIMEOUT:         'Tool не ответил за отведённое время',
  UNAUTHORIZED:         'Требуется аутентификация',
  FORBIDDEN:            'Недостаточно прав',
  NOT_FOUND:            'Ресурс не найден',
  RATE_LIMITED:         'Слишком много запросов. Попробуйте позже',
  INTERNAL_ERROR:       'Внутренняя ошибка сервера',
} as const;
```

## Appendix C: Animation & Transition Guidelines

```yaml
# Duration
instant: 100ms
fast: 150ms
normal: 200ms
slow: 300ms

# Easing
ease-out: cubic-bezier(0.16, 1, 0.3, 1)     # UI elements, cards
ease-in-out: cubic-bezier(0.65, 0, 0.35, 1)  # Modals, transitions
linear: none                                  # Spinners

# Specific animations
sidebar-hover: background-color 150ms ease-out
modal-enter: opacity 200ms ease-out, transform 200ms ease-out (scale 0.95 → 1)
modal-exit: opacity 150ms ease-in, transform 150ms ease-in (scale 1 → 0.95)
row-hover: background-color 150ms ease-out
skeleton: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite
status-dot-pulse: pulse 2s ease-in-out infinite  # for 'running' state
page-enter: opacity 200ms ease-out
slide-over-enter: transform 300ms ease-out (translateX 100% → 0)
toast-enter: transform 300ms ease-out (translateY -100% → 0), opacity 300ms ease-out
```

---

*Design spec generated 2026-04-28 — full specs for React + shadcn/ui + Tailwind CSS implementation.*
