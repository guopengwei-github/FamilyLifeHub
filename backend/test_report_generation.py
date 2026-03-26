"""测试 id=2 用户的早报和晚报生成（带数据注入）"""
import sys
import asyncio
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')

# 设置 Python 路径
sys.path.insert(0, 'D:\\ai\\family_life_hub\\backend')

from app.core.database import SessionLocal
from app.services.report_data_aggregator import aggregate_morning_report_data, aggregate_evening_report_data
from app.services.llm.prompts import format_morning_report_prompt, format_evening_report_prompt

async def test_reports():
    db = SessionLocal()
    user_id = 2
    report_date = date.today()
    
    try:
        print(f"\n{'='*60}")
        print(f"测试 id={user_id} 用户的报告生成")
        print(f"报告日期: {report_date}")
        print(f"{'='*60}\n")
        
        # ========== 早报测试 ==========
        print(f"【1】早报数据聚合")
        print(f"{'='*60}")
        
        morning_data = aggregate_morning_report_data(db, user_id, report_date)
        
        # 打印关键数据
        print(f"\n用户画像:")
        if morning_data.get('user_profile'):
            for k, v in morning_data['user_profile'].items():
                print(f"  {k}: {v}")
        
        print(f"\n睡眠数据:")
        if morning_data.get('sleep_data'):
            if morning_data['sleep_data'].get('last_night'):
                print(f"  昨晚睡眠: {morning_data['sleep_data']['last_night']}")
            if morning_data['sleep_data'].get('trend_7d'):
                print(f"  7日趋势: {morning_data['sleep_data']['trend_7d']}")
        
        print(f"\n身体电量:")
        if morning_data.get('body_battery'):
            print(f"  {morning_data['body_battery']}")
        
        print(f"\nHRV 数据:")
        if morning_data.get('hrv_data'):
            print(f"  {morning_data['hrv_data']}")
        
        # 生成早报提示词
        print(f"\n{'='*60}")
        print(f"【2】早报提示词")
        print(f"{'='*60}\n")
        
        morning_prompt = format_morning_report_prompt(
            report_date=report_date,
            sleep_data=morning_data['sleep_data'],
            hrv_data=morning_data['hrv_data'],
            body_battery=morning_data['body_battery'],
            activity_data=morning_data['activity_data'],
            user_profile=morning_data['user_profile'],
            sleep_metrics=morning_data.get('sleep_metrics'),
            sleep_charging_efficiency=morning_data.get('sleep_charging_efficiency'),
            sleep_structure=morning_data.get('sleep_structure'),
            recovery_quality=morning_data.get('recovery_quality'),
            yesterday_workout=morning_data.get('yesterday_workout')
        )
        
        print(morning_prompt)
        
        # 保存到文件
        with open('D:\\ai\\family_life_hub\\backend\\test_morning_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(morning_prompt)
        print(f"\n✓ 早报提示词已保存到 test_morning_prompt.txt")
        
        # ========== 晚报测试 ==========
        print(f"\n\n{'='*60}")
        print(f"【3】晚报数据聚合")
        print(f"{'='*60}")
        
        evening_data = aggregate_evening_report_data(db, user_id, report_date)
        
        # 打印关键数据
        print(f"\n心率数据:")
        if evening_data.get('heart_rate_data'):
            print(f"  {evening_data['heart_rate_data']}")
        
        print(f"\n压力数据:")
        if evening_data.get('stress_data'):
            if evening_data['stress_data'].get('today'):
                print(f"  今日压力: {evening_data['stress_data']['today']}")
            if evening_data['stress_data'].get('avg_7d'):
                print(f"  7日平均: {evening_data['stress_data']['avg_7d']}")
        
        print(f"\n身体电量:")
        if evening_data.get('body_battery'):
            bb = evening_data['body_battery']
            print(f"  今晨起始值: {bb.get('morning_value')}")
            print(f"  当前值: {bb.get('current_value')}")
            print(f"  今日消耗: {bb.get('consumed')}")
            print(f"  3日平均消耗: {bb.get('comparison_3d')}")
        
        print(f"\n活动数据:")
        if evening_data.get('activity_data'):
            if evening_data['activity_data'].get('today'):
                print(f"  今日活动: {evening_data['activity_data']['today']}")
            if evening_data['activity_data'].get('avg_7d'):
                print(f"  7日平均: {evening_data['activity_data']['avg_7d']}")
        
        # 生成晚报提示词
        print(f"\n{'='*60}")
        print(f"【4】晚报提示词")
        print(f"{'='*60}\n")
        
        evening_prompt = format_evening_report_prompt(
            report_date=report_date,
            heart_rate_data=evening_data['heart_rate_data'],
            stress_data=evening_data['stress_data'],
            body_battery=evening_data['body_battery'],
            activity_data=evening_data['activity_data'],
            user_profile=evening_data['user_profile'],
            resting_hr=evening_data.get('resting_hr'),
            workout_data=evening_data.get('workout_data'),
            heart_rate_zones=evening_data.get('heart_rate_zones'),
            energy_curve=evening_data.get('energy_curve')
        )
        
        print(evening_prompt)
        
        # 保存到文件
        with open('D:\\ai\\family_life_hub\\backend\\test_evening_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(evening_prompt)
        print(f"\n✓ 晚报提示词已保存到 test_evening_prompt.txt")
        
        # ========== 数据验证 ==========
        print(f"\n\n{'='*60}")
        print(f"【5】数据验证")
        print(f"{'='*60}\n")
        
        # 验证早报数据
        print("早报数据验证:")
        if morning_data.get('body_battery'):
            morning_bb = morning_data['body_battery'].get('morning_value')
            print(f"  ✓ 身体电量（早报）: {morning_bb}")
            if morning_bb == 29:
                print(f"  ✅ 早报身体电量正确！")
            else:
                print(f"  ⚠️ 早报身体电量可能不正确（预期: 29, 实际: {morning_bb}）")
        
        # 验证晚报数据
        print("\n晚报数据验证:")
        if evening_data.get('body_battery'):
            evening_morning_bb = evening_data['body_battery'].get('morning_value')
            evening_current_bb = evening_data['body_battery'].get('current_value')
            print(f"  ✓ 身体电量（今晨）: {evening_morning_bb}")
            print(f"  ✓ 身体电量（当前）: {evening_current_bb}")
            
            if evening_morning_bb == 29 and evening_current_bb == 29:
                print(f"  ✅ 晚报身体电量正确！")
            else:
                print(f"  ⚠️ 晚报身体电量可能不正确（预期: 29, 实际: {evening_morning_bb}/{evening_current_bb}）")
        
        print(f"\n{'='*60}")
        print(f"测试完成！")
        print(f"{'='*60}")
        
    finally:
        db.close()

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_reports())
