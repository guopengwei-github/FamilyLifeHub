#!/usr/bin/env python
"""
独立晚报生成脚本

用于 cron 任务调用,生成所有活跃用户的晚报。
"""
import asyncio
import sys
import os
from pathlib import Path

# 确保项目根目录在 Python 路径中
backend_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(backend_dir))

# 切换工作目录以确保 .env 文件被正确加载
os.chdir(backend_dir)

from app.tasks.scheduler import generate_evening_reports_job


async def main():
    """执行晚报生成任务"""
    print("开始执行晚报生成任务...")
    try:
        await generate_evening_reports_job()
        print("晚报生成任务完成")
        return 0
    except Exception as e:
        print(f"晚报生成任务失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
