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

- ❌ 错误尝试：反复尝试杀同一批 PID
  - 原因：进程可能已死，但 netstat 仍显示端口占用（僵尸连接、TIME_WAIT 等）
  - 正确做法：taskkill 失败后直接忽略，继续启动服务

## 3. 成功工作流 (Best Practices)

1. **查找占用端口的进程**
   ```bash
   netstat -ano | findstr ":3000 :3001 :8000" | findstr LISTENING
   ```

2. **杀掉现有进程**（注意双斜杠语法，忽略"进程不存在"错误）
   ```bash
   # 尝试杀进程，失败就忽略（进程可能已死）
   taskkill //F //PID <pid> 2>/dev/null || true
   ```

3. **如果按 PID 杀不掉，尝试按程序名杀**（备选方案）
   ```bash
   taskkill //F //IM python.exe 2>/dev/null
   taskkill //F //IM node.exe 2>/dev/null
   ```

4. **直接启动服务**（不要反复检查端口）
   - 如果端口真的被占用，服务启动会报错
   - 直接尝试启动比反复检查更高效

5. **后台启动后端服务**
   ```bash
   cd D:/ai/family_life_hub/backend
   venv/Scripts/python.exe main.py
   ```

6. **后台启动前端服务**
   ```bash
   cd D:/ai/family_life_hub/frontend && npm run dev
   ```

## 4. 核心代码与配置参考

### 完整重启脚本（Windows Git Bash）

```bash
# 1. 查找占用端口的 PID
netstat -ano | findstr ":3000 :8000" | findstr LISTENING

# 2. 尝试杀掉进程（失败就忽略，进程可能已死）
for pid in <pid1> <pid2> <pid3>; do
  taskkill //F //PID $pid 2>/dev/null || true
done

# 3. 如果还有残留，按程序名杀（备选方案）
taskkill //F //IM python.exe 2>/dev/null || true
taskkill //F //IM node.exe 2>/dev/null || true

# 4. 直接启动服务（不要反复检查端口）
cd D:/ai/family_life_hub/backend && venv/Scripts/python.exe main.py &
cd D:/ai/family_life_hub/frontend && npm run dev &

# 5. 等待几秒后验证服务是否启动
sleep 3 && netstat -ano | findstr ":3000 :8000" | findstr LISTENING
```

### 重要提示

- **不要反复检查端口再杀进程**：netstat 可能显示已死进程的端口占用
- **一次杀不掉就放弃**：用 `2>/dev/null || true` 静默错误并继续
- **直接启动服务**：让服务自己报错是否端口真正被占用
- **备选方案**：按程序名 (`//IM`) 杀进程可以清理残留

### 服务端口配置

| 服务 | 端口 | URL |
|------|------|-----|
| 后端 API | 8000 | http://localhost:8000 |
| 前端 | 3000 | http://localhost:3000 |
