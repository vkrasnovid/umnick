"""
Tests for the Proactive Engine — watcher evaluator, dedup, templates.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestDedup:
    """Test alert deduplication logic."""

    def test_compute_alert_hash(self):
        from watcher.dedup import compute_alert_hash

        tool_response = {
            "success": True,
            "data": {
                "summary": {
                    "total_overdue_count": 5,
                    "total_overdue_sum": 100000.0,
                }
            }
        }

        h = compute_alert_hash("get_overdue_payments", {"days_overdue_min": 1}, tool_response)
        assert h
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex digest

    def test_compute_hash_deterministic(self):
        from watcher.dedup import compute_alert_hash

        tool_response = {"data": {"summary": {"count": 1}}}
        h1 = compute_alert_hash("tool", {"p": 1}, tool_response)
        h2 = compute_alert_hash("tool", {"p": 1}, tool_response)
        assert h1 == h2

    def test_compute_hash_different_params(self):
        from watcher.dedup import compute_alert_hash

        tool_response = {"data": {"summary": {"count": 1}}}
        h1 = compute_alert_hash("tool", {"p": 1}, tool_response)
        h2 = compute_alert_hash("tool", {"p": 2}, tool_response)
        assert h1 != h2

    def test_should_send_different_hash(self):
        from watcher.dedup import should_send_alert

        result = should_send_alert(
            tool_response={"data": {}},
            current_hash="new_hash",
            last_alert_hash="old_hash",
            snooze_until=None,
        )
        assert result is True

    def test_should_not_send_same_hash(self):
        from watcher.dedup import should_send_alert

        result = should_send_alert(
            tool_response={"data": {}},
            current_hash="same_hash",
            last_alert_hash="same_hash",
            snooze_until=None,
        )
        assert result is False

    def test_should_not_send_snoozed(self):
        from watcher.dedup import should_send_alert

        result = should_send_alert(
            tool_response={"data": {}},
            current_hash="new",
            last_alert_hash="old",
            snooze_until=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        assert result is False

    def test_should_send_no_last_hash(self):
        from watcher.dedup import should_send_alert

        result = should_send_alert(
            tool_response={"data": {}},
            current_hash="hash",
            last_alert_hash=None,
            snooze_until=None,
        )
        assert result is True

    def test_should_send_snooze_expired(self):
        from watcher.dedup import should_send_alert

        result = should_send_alert(
            tool_response={"data": {}},
            current_hash="new_hash",
            last_alert_hash="old_hash",
            snooze_until=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        assert result is True


class TestTemplate:
    """Test Jinja2 template rendering."""

    def test_render_simple(self):
        from watcher.template import render_message

        result = render_message("Count: {{data.count}}", {"count": 42})
        assert result == "Count: 42"

    def test_render_object(self):
        from watcher.template import render_message

        template = "Name: {{data.name}}, Value: {{data.value}}"
        result = render_message(template, {"name": "Test", "value": 100})
        assert result == "Name: Test, Value: 100"

    def test_render_number_filter(self):
        from watcher.template import render_message

        template = "Sum: {{data.sum | number}}"
        result = render_message(template, {"sum": 1234567.89})
        assert "1,234,567.89" in result

    def test_render_round_filter(self):
        from watcher.template import render_message

        template = "Pct: {{data.pct | round(1)}}"
        result = render_message(template, {"pct": 25.333})
        assert "25.3" in result

    def test_render_for_loop(self):
        from watcher.template import render_message

        template = "{% for item in data['list'] %}- {{item}}\n{% endfor %}"
        result = render_message(template, {"list": ["A", "B", "C"]})
        assert "- A\n" in result
        assert "- B\n" in result
        assert "- C\n" in result

    def test_render_overdue_template(self):
        from watcher.template import render_message

        template = (
            "📋 *Ежедневный отчёт по просрочкам*\n\n"
            "Всего просроченных счетов: *{{data.summary.total_overdue_count}}*\n"
            "Общая сумма: *{{data.summary.total_overdue_sum | number}}₽*"
        )
        data = {
            "summary": {
                "total_overdue_count": 5,
                "total_overdue_sum": 145800.00,
            }
        }
        result = render_message(template, data)
        assert "5" in result
        assert "145,800.00" in result

    def test_render_undefined(self):
        from watcher.template import render_message

        template = "{{data.undefined_field}}"
        # Undefined values render as empty string
        result = render_message(template, {"some": "data"})
        assert result == ""


class TestConditionEval:
    """Test condition evaluation."""

    def test_condition_true(self):
        from tasks import _evaluate_condition

        tool_response = {
            "data": {
                "summary": {
                    "total_overdue_count": 5,
                    "total_overdue_sum": 100000.0,
                }
            }
        }
        result = _evaluate_condition("data.summary.total_overdue_count > 0", tool_response)
        assert result is True

    def test_condition_false(self):
        from tasks import _evaluate_condition

        tool_response = {
            "data": {
                "summary": {
                    "total_overdue_count": 0,
                    "total_overdue_sum": 0,
                }
            }
        }
        result = _evaluate_condition("data.summary.total_overdue_count > 0", tool_response)
        assert result is False

    def test_condition_edge_zero(self):
        from tasks import _evaluate_condition

        tool_response = {"data": {"count": 0}}
        result = _evaluate_condition("data.count > 0", tool_response)
        assert result is False

    def test_condition_with_len(self):
        from tasks import _evaluate_condition

        tool_response = {"data": {"items": [1, 2, 3]}}
        result = _evaluate_condition("len(data.items) >= 2", tool_response)
        assert result is True

    def test_condition_no_data(self):
        from tasks import _evaluate_condition

        result = _evaluate_condition("data.overdue_count > 0", {"data": {}})
        assert result is False


class TestCeleryConfig:
    """Test Celery app configuration."""

    def test_celery_app_exists(self):
        from celery_app import celery_app

        assert celery_app is not None
        assert celery_app.main == "umnick_engine"

    def test_beat_schedule(self):
        from celery_app import celery_app

        assert "check-watchers-every-minute" in celery_app.conf.beat_schedule
        schedule = celery_app.conf.beat_schedule["check-watchers-every-minute"]
        assert schedule["task"] == "tasks.check_due_watchers"
        assert schedule["schedule"] == 60.0


class TestEngineMessages:
    """Test engine Russian messages."""

    def test_messages_defined(self):
        from messages_ru import WATCHER_NO_ALERTS, TOOL_ERROR

        assert WATCHER_NO_ALERTS
        assert TOOL_ERROR
