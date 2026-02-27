---
name: restart-project
description: 重启 FamilyLifeHub 项目的前后端服务。当用户说"重启项目"、"restart"或服务无响应时自动触发。
---

## 1. 适用场景与目标

- 用户请求重启项目
- 前端或后端服务无响应
- 端口被占用需要重新启动服务
- 代码更新后需要重启服务生效

目标：安全地停止现有进程，然后启动新的后端和前端服务。

## 2. 避坑指南 (Anti-Patterns)

- ❌ 错误尝试：直接启动服务而不先杀掉现有进程
  - 原因：端口已被占用会导致启动失败

- ❌ 错误尝试：在 Windows Git Bash 中使用 `taskkill /F /PID xxx`
  - 原因：斜杠会被解释为路径，导致 "无效参数/选项" 错误
  - 正确写法：使用双斜杠 `taskkill //F //PID xxx`

- ❌ 错误尝试：使用 Linux 风格的 `timeout 3` 命令
  - 原因：Windows 的 timeout 命令语法不同

- ❌ 错误尝试：使用 `grep` 和 `awk` 处理 Windows 命令输出
  - 原因：应使用 `findstr` 替代 `grep`

## 3. 成功工作流 (Best Practices)

1. **查找占用端口的进程**
   ```bash
   netstat -ano | findstr ":3000 :3001 :8000" | findstr LISTENING
   ```

2. **杀掉现有进程**（注意双斜杠语法）
   ```bash
   taskkill //F //PID <pid>
   ```

3. **后台启动后端服务**
   ```bash
   cd D:/ai/family_life_hub/backend 
   venv/Scripts/python.exe main.py
   ```

4. **后台启动前端服务**
   ```bash
   cd D:/ai/family_life_hub/frontend && npm run dev
   ```

## 4. 核心代码与配置参考

### 完整重启脚本（Windows Git Bash）

```bash
# 1. 查找并记录占用端口的 PID
netstat -ano | findstr ":3000  :8000" | findstr LISTENING

# 2. 杀掉进程（替换为实际 PID）
taskkill //F //PID <frontend_pid>
taskkill //F //PID <backend_pid>

# 3. 启动后端（后台运行）
cd D:/ai/family_life_hub/backend && venv/Scripts/python.exe main.py

# 4. 启动前端（后台运行）
cd D:/ai/family_life_hub/frontend && npm run dev &
```

### 服务端口配置

| 服务 | 端口 | URL |
|------|------|-----|
| 后端 API | 8000 | http://localhost:8000 |
| 前端 | 3000 | http://localhost:3000 |
