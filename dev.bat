@echo off
chcp 65001 >nul
echo ========================================
echo FamilyLifeHub 本地开发环境启动
echo ========================================
echo.

echo [1/2] 启动后端服务 (FastAPI)...
start "FamilyLifeHub Backend" cmd /k "cd backend && python -m venv venv 2>nul && venv\Scripts\activate && pip install -r requirements.txt --quiet && echo 后端服务启动中... && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务 (Next.js)...
start "FamilyLifeHub Frontend" cmd /k "cd frontend && call npm install --silent && echo 前端服务启动中... && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo 启动完成!
echo 前端: http://localhost:3000
echo 后端: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo ========================================
echo.
echo 按 Ctrl+C 关闭此窗口不会影响服务
echo 请手动关闭前后端窗口来停止服务
