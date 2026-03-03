"""
Tests for prompt templates.
"""
import pytest
from datetime import date

from app.services.llm.prompts import (
    MORNING_REPORT_SYSTEM_PROMPT,
    EVENING_REPORT_SYSTEM_PROMPT,
    format_morning_report_prompt,
    format_evening_report_prompt
)


class TestPromptConstants:
    """Test prompt constants exist."""

    def test_morning_system_prompt_exists(self):
        """Morning system prompt should be defined."""
        assert MORNING_REPORT_SYSTEM_PROMPT is not None
        assert len(MORNING_REPORT_SYSTEM_PROMPT) > 100
        assert "系统恢复评估" in MORNING_REPORT_SYSTEM_PROMPT

    def test_evening_system_prompt_exists(self):
        """Evening system prompt should be defined."""
        assert EVENING_REPORT_SYSTEM_PROMPT is not None
        assert len(EVENING_REPORT_SYSTEM_PROMPT) > 100
        assert "今日消耗总结" in EVENING_REPORT_SYSTEM_PROMPT


class TestFormatMorningReportPrompt:
    """Test morning report prompt formatting."""

    def test_basic_formatting(self):
        """Should format with minimal data."""
        result = format_morning_report_prompt(
            report_date=date(2026, 3, 1),
            sleep_data=None,
            hrv_data=None,
            body_battery=None,
            activity_data=None
        )
        assert "2026年03月01日" in result
        assert "晨间精力报告" in result

    def test_with_user_profile(self):
        """Should include user profile."""
        result = format_morning_report_prompt(
            report_date=date(2026, 3, 1),
            sleep_data=None,
            hrv_data=None,
            body_battery=None,
            activity_data=None,
            user_profile={'age': 30, 'gender': 'male', 'weight_kg': 70}
        )
        assert "年龄: 30岁" in result
        assert "性别: 男" in result
        assert "体重: 70kg" in result

    def test_with_sleep_data(self):
        """Should include sleep data."""
        result = format_morning_report_prompt(
            report_date=date(2026, 3, 1),
            sleep_data={
                'last_night': {
                    'total_sleep_hours': 7.5,
                    'deep_sleep_hours': 1.5,
                    'light_sleep_hours': 4.0,
                    'rem_sleep_hours': 2.0,
                    'sleep_score': 85
                },
                'trend_7d': {'avg_sleep_hours': 7.2}
            },
            hrv_data=None,
            body_battery=None,
            activity_data=None
        )
        assert "昨晚睡眠: 7.5小时" in result
        assert "深睡: 1.5小时" in result
        assert "睡眠评分: 85" in result
        assert "7日平均: 7.2小时" in result

    def test_with_hrv_data(self):
        """Should include HRV data in sleep recovery section."""
        result = format_morning_report_prompt(
            report_date=date(2026, 3, 1),
            sleep_data=None,
            hrv_data={
                'last_night': {'avg_hrv': 45},
                'avg_7d': 42,
                'trend_3d': '上升'
            },
            body_battery=None,
            activity_data=None
        )
        # HRV now in sleep recovery section with combined format
        assert "睡眠期间恢复指标" in result
        assert "HRV: 45ms" in result
        assert "7日均值: 42ms" in result
        assert "3日趋势: 上升" in result

    def test_with_body_battery(self):
        """Should include body battery data."""
        result = format_morning_report_prompt(
            report_date=date(2026, 3, 1),
            sleep_data=None,
            hrv_data=None,
            body_battery={'morning_value': 85},
            activity_data=None
        )
        assert "今晨起始值: 85" in result

    def test_with_body_battery_sleep_recovery(self):
        """Should include body battery before/after sleep data."""
        result = format_morning_report_prompt(
            report_date=date(2026, 3, 1),
            sleep_data=None,
            hrv_data=None,
            body_battery={
                'before_sleep': 25,
                'after_sleep': 68,
                'charged': 43
            },
            activity_data=None
        )
        assert "入睡前: 25" in result
        assert "醒来后: 68" in result
        assert "睡眠补充: +43" in result

    def test_with_sleep_metrics(self):
        """Should include sleep period metrics."""
        result = format_morning_report_prompt(
            report_date=date(2026, 3, 1),
            sleep_data=None,
            hrv_data=None,
            body_battery=None,
            activity_data=None,
            sleep_metrics={
                'spo2': 96.5,
                'respiration_rate': 14.2,
                'stress_level': 18,
                'resting_hr': 58
            }
        )
        assert "睡眠血氧饱和度: 96.5%" in result
        assert "睡眠呼吸频率: 14.2 次/分钟" in result
        assert "睡眠期间压力: 18" in result
        assert "静息心率: 58 bpm" in result


class TestFormatEveningReportPrompt:
    """Test evening report prompt formatting."""

    def test_basic_formatting(self):
        """Should format with minimal data."""
        result = format_evening_report_prompt(
            report_date=date(2026, 3, 1),
            heart_rate_data=None,
            stress_data=None,
            body_battery=None,
            activity_data=None
        )
        assert "2026年03月01日" in result
        assert "晚间复盘报告" in result

    def test_with_stress_data(self):
        """Should include stress data."""
        result = format_evening_report_prompt(
            report_date=date(2026, 3, 1),
            heart_rate_data=None,
            stress_data={
                'today': {
                    'avg_stress': 35,
                    'high_stress_minutes': 60,
                    'medium_stress_minutes': 120,
                    'low_stress_minutes': 180,
                    'rest_stress_minutes': 240
                },
                'avg_7d': 38
            },
            body_battery=None,
            activity_data=None
        )
        # Updated to match new "全天压力分布" section
        assert "全天压力分布" in result
        assert "今日全天平均压力: 35" in result
        assert "高压力时长: 60分钟" in result
        assert "7日平均压力: 38" in result

    def test_with_body_battery_consumption(self):
        """Should include body battery consumption."""
        result = format_evening_report_prompt(
            report_date=date(2026, 3, 1),
            heart_rate_data=None,
            stress_data=None,
            body_battery={
                'morning_value': 90,
                'current_value': 25,
                'consumed': 65,
                'comparison_3d': 70
            },
            activity_data=None
        )
        assert "今晨起始值: 90" in result
        assert "当前值: 25" in result
        # Consumption now shows as negative value
        assert "今日消耗: -65" in result
        assert "3日平均消耗: 70" in result

    def test_with_resting_hr(self):
        """Should include resting heart rate in evening report."""
        result = format_evening_report_prompt(
            report_date=date(2026, 3, 1),
            heart_rate_data=None,
            stress_data=None,
            body_battery=None,
            activity_data=None,
            resting_hr=56
        )
        assert "静息心率(睡眠期间): 56 bpm" in result
