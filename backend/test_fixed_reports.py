"""测试修复后的早报和晚报数据聚合"""
import sys
import asyncio
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'D:\\ai\\family_life_hub\\backend')

from app.core.database import SessionLocal
from app.services.report_data_aggregator import aggregate_morning_report_data, aggregate_evening_report_data

async def test_reports():
    db = SessionLocal()
    user_id = 2
    report_date = date.today()
    
    try:
        print(f"\n{'='*60}")
        print(f"测试修复后的报告数据聚合")
        print(f"报告日期: {report_date}")
        print(f"{'='*60}\n")
        
        # 早报测试
        print(f"【早报数据】")
        print(f"{'='*60}")
        
        morning_data = aggregate_morning_report_data(db, user_id, report_date)
        
        if morning_data.get('body_battery'):
            bb = morning_data['body_battery']
            print(f"身体电量:")
            print(f"  今晨起始值: {bb.get('morning_value')}")
            print(f"  睡眠后: {bb.get('after_sleep')}")
            print(f"  睡眠前: {bb.get('before_sleep')}")
            print(f"  充电量: {bb.get('charged')}")
            
            if bb.get('morning_value') == 97:
                print(f"\n  ✅ 早报身体电量正确！")
            else:
                print(f"\n  ❌ 早报身体电量错误（预期: 97, 实际: {bb.get('morning_value')}）")
        
        # 晚报测试
        print(f"\n【晚报数据】")
        print(f"{'='*60}")
        
        evening_data = aggregate_evening_report_data(db, user_id, report_date)
        
        if evening_data.get('body_battery'):
            bb = evening_data['body_battery']
            print(f"身体电量:")
            print(f"  今晨起始值: {bb.get('morning_value')}")
            print(f"  当前值: {bb.get('current_value')}")
            print(f"  今日消耗: {bb.get('consumed')}")
            print(f"  3日平均消耗: {bb.get('comparison_3d')}")
            
            if bb.get('current_value') == 29:
                print(f"\n  ✅ 晚报身体电量正确！")
            else:
                print(f"\n  ❌ 晚报身体电量错误（预期: 29, 实际: {bb.get('current_value')}）")
        
        print(f"\n{'='*60}")
        print(f"测试完成！")
        print(f"{'='*60}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_reports())
