"""
Prompt templates for health report generation.

Contains system prompts and data formatting functions for
morning and evening health reports.
"""
from datetime import date


# System prompt for morning readiness report
MORNING_REPORT_SYSTEM_PROMPT = """你是一位专业的健康与精力管理顾问。你的任务是分析用户的睡眠、HRV、身体电量等生理数据，结合历史趋势，为用户提供个性化的晨间精力评估和今日安排建议。

你的回复必须使用 Markdown 格式，包含以下部分：

## 系统恢复评估
分析昨晚的睡眠质量、HRV 水平和今晨身体电量，评估用户的恢复状态。

## 今日安排建议
基于恢复状态，给出今日的工作、午睡、脑力活动建议：
- 🎯 重点任务时段建议
- 😴 午休建议（是否需要、最佳时长）
- 🧠 脑力活动强度建议

## 今日运动处方
根据身体状态，推荐今日的运动类型和强度。

注意：
- 使用客观、专业的语气
- 建议要具体、可操作
- 如果数据异常，提醒用户关注
"""

# System prompt for evening review report
EVENING_REPORT_SYSTEM_PROMPT = """你是一位专业的健康与精力管理顾问。你的任务是分析用户全天的生理数据（心率、压力、身体电量消耗、活动），结合历史趋势，为用户提供晚间复盘和明日优化建议。

你的回复必须使用 Markdown 格式，包含以下部分：

## 今日消耗总结
总结今天的身体电量消耗、压力分布和活动情况。

## 高压精准归因
分析今天的高压力时段，尝试找出可能的原因（基于活动数据推断）。

## 明日优化建议
基于今天的消耗和恢复情况，给出明天的优化建议。

## 今晚入睡干预
给出今晚的睡眠建议，包括：
- 建议入睡时间
- 睡前准备建议
- 是否需要放松活动

注意：
- 使用客观、专业的语气
- 建议要具体、可操作
- 如果发现异常模式，提醒用户关注
"""


def format_morning_report_prompt(
    report_date: date,
    sleep_data: dict | None,
    hrv_data: dict | None,
    body_battery: dict | None,
    activity_data: dict | None,
    user_profile: dict | None = None
) -> str:
    """
    Format the morning report prompt with user data.

    Args:
        report_date: The date of the report.
        sleep_data: Last night's sleep data + 7-day trend.
        hrv_data: HRV data + 7-day average + 3-day trend.
        body_battery: This morning's starting body battery.
        activity_data: Past 3 days of exercise data.
        user_profile: Optional user profile (age, gender, weight).

    Returns:
        Formatted prompt string.
    """
    sections = []

    # Header
    sections.append(f"# 晨间精力报告 - {report_date.strftime('%Y年%m月%d日')}")
    sections.append("")

    # User profile
    if user_profile:
        sections.append("## 用户画像")
        profile_parts = []
        if user_profile.get('age'):
            profile_parts.append(f"年龄: {user_profile['age']}岁")
        if user_profile.get('gender'):
            gender_map = {'male': '男', 'female': '女', 'other': '其他'}
            profile_parts.append(f"性别: {gender_map.get(user_profile['gender'], user_profile['gender'])}")
        if user_profile.get('weight_kg'):
            profile_parts.append(f"体重: {user_profile['weight_kg']}kg")
        sections.append(" | ".join(profile_parts))
        sections.append("")

    # Sleep data
    if sleep_data:
        sections.append("## 睡眠数据")
        if sleep_data.get('last_night'):
            ln = sleep_data['last_night']
            sections.append(f"- 昨晚睡眠: {ln.get('total_sleep_hours', 'N/A')}小时")
            sections.append(f"  - 深睡: {ln.get('deep_sleep_hours', 'N/A')}小时")
            sections.append(f"  - 浅睡: {ln.get('light_sleep_hours', 'N/A')}小时")
            sections.append(f"  - REM: {ln.get('rem_sleep_hours', 'N/A')}小时")
            sections.append(f"  - 睡眠评分: {ln.get('sleep_score', 'N/A')}")
        if sleep_data.get('trend_7d'):
            t7 = sleep_data['trend_7d']
            sections.append(f"- 7日平均: {t7.get('avg_sleep_hours', 'N/A')}小时")
        sections.append("")

    # HRV data
    if hrv_data:
        sections.append("## HRV 数据")
        if hrv_data.get('last_night'):
            sections.append(f"- 昨夜HRV: {hrv_data['last_night'].get('avg_hrv', 'N/A')}ms")
        if hrv_data.get('avg_7d'):
            sections.append(f"- 7日均值: {hrv_data['avg_7d']}ms")
        if hrv_data.get('trend_3d'):
            sections.append(f"- 3日趋势: {hrv_data['trend_3d']}")
        sections.append("")

    # Body battery
    if body_battery:
        sections.append("## 身体电量")
        sections.append(f"- 今晨起始值: {body_battery.get('morning_value', 'N/A')}")
        sections.append("")

    # Activity data
    if activity_data:
        sections.append("## 近期活动 (过去3天)")
        for day in activity_data.get('days', []):
            sections.append(f"- {day.get('date', 'N/A')}: {day.get('activity_type', 'N/A')} {day.get('duration_min', 'N/A')}分钟")
        sections.append("")

    sections.append("---")
    sections.append("请根据以上数据，生成今日的晨间精力报告。")

    return "\n".join(sections)


def format_evening_report_prompt(
    report_date: date,
    heart_rate_data: dict | None,
    stress_data: dict | None,
    body_battery: dict | None,
    activity_data: dict | None,
    user_profile: dict | None = None
) -> str:
    """
    Format the evening report prompt with user data.

    Args:
        report_date: The date of the report.
        heart_rate_data: Today's heart rate + 7-day comparison.
        stress_data: Today's stress distribution + 7-day comparison.
        body_battery: Today's consumption + 3-day comparison.
        activity_data: Today's activity + 7-day comparison.
        user_profile: Optional user profile.

    Returns:
        Formatted prompt string.
    """
    sections = []

    # Header
    sections.append(f"# 晚间复盘报告 - {report_date.strftime('%Y年%m月%d日')}")
    sections.append("")

    # User profile
    if user_profile:
        sections.append("## 用户画像")
        profile_parts = []
        if user_profile.get('age'):
            profile_parts.append(f"年龄: {user_profile['age']}岁")
        if user_profile.get('gender'):
            gender_map = {'male': '男', 'female': '女', 'other': '其他'}
            profile_parts.append(f"性别: {gender_map.get(user_profile['gender'], user_profile['gender'])}")
        if user_profile.get('weight_kg'):
            profile_parts.append(f"体重: {user_profile['weight_kg']}kg")
        sections.append(" | ".join(profile_parts))
        sections.append("")

    # Heart rate data
    if heart_rate_data:
        sections.append("## 心率数据")
        if heart_rate_data.get('today'):
            sections.append(f"- 今日平均心率: {heart_rate_data['today'].get('avg_hr', 'N/A')} bpm")
            sections.append(f"- 今日最高心率: {heart_rate_data['today'].get('max_hr', 'N/A')} bpm")
            sections.append(f"- 今日最低心率: {heart_rate_data['today'].get('min_hr', 'N/A')} bpm")
        if heart_rate_data.get('avg_7d'):
            sections.append(f"- 7日平均心率: {heart_rate_data['avg_7d']} bpm")
        sections.append("")

    # Stress data
    if stress_data:
        sections.append("## 压力分布")
        if stress_data.get('today'):
            sections.append(f"- 今日平均压力: {stress_data['today'].get('avg_stress', 'N/A')}")
            sections.append(f"- 高压力时长: {stress_data['today'].get('high_stress_minutes', 'N/A')}分钟")
            sections.append(f"- 中压力时长: {stress_data['today'].get('medium_stress_minutes', 'N/A')}分钟")
            sections.append(f"- 低压力时长: {stress_data['today'].get('low_stress_minutes', 'N/A')}分钟")
            sections.append(f"- 放松时长: {stress_data['today'].get('rest_stress_minutes', 'N/A')}分钟")
        if stress_data.get('avg_7d'):
            sections.append(f"- 7日平均压力: {stress_data['avg_7d']}")
        sections.append("")

    # Body battery
    if body_battery:
        sections.append("## 身体电量消耗")
        sections.append(f"- 今晨起始值: {body_battery.get('morning_value', 'N/A')}")
        sections.append(f"- 当前值: {body_battery.get('current_value', 'N/A')}")
        sections.append(f"- 今日消耗: {body_battery.get('consumed', 'N/A')}")
        if body_battery.get('comparison_3d'):
            sections.append(f"- 3日平均消耗: {body_battery['comparison_3d']}")
        sections.append("")

    # Activity data
    if activity_data:
        sections.append("## 活动数据")
        if activity_data.get('today'):
            sections.append(f"- 今日活动: {activity_data['today'].get('total_steps', 'N/A')}步")
            sections.append(f"- 活动时长: {activity_data['today'].get('active_minutes', 'N/A')}分钟")
            sections.append(f"- 消耗卡路里: {activity_data['today'].get('calories', 'N/A')}kcal")
        if activity_data.get('avg_7d'):
            sections.append(f"- 7日平均步数: {activity_data['avg_7d']}步")
        sections.append("")

    sections.append("---")
    sections.append("请根据以上数据，生成今日的晚间复盘报告。")

    return "\n".join(sections)
