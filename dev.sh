#!/bin/bash

echo "========================================"
echo "FamilyLifeHub 本地开发环境启动"
echo "========================================"
echo ""

# 启动后端
echo "[1/2] 启动后端服务 (FastAPI)..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..
sleep 3

# 启动前端
echo "[2/2] 启动前端服务 (Next.js)..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..
sleep 3

echo ""
echo "========================================"
echo "启动完成!"
echo "前端: http://localhost:3000"
echo "后端: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

wait
