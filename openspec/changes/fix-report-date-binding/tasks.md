## 1. 前端修复

- [ ] 1.1 修改 `frontend/app/page.tsx`，将 `date` prop 传递给 `MorningReport` 和 `EveningReport` 组件
- [ ] 1.2 更新 `frontend/components/reports/morning-report.tsx` 中的错误提示，去掉"今日"
- [ ] 1.3 更新 `frontend/components/reports/evening-report.tsx` 中的错误提示，去掉"今日"

## 2. 验证

- [ ] 2.1 手动测试：选择今天日期，验证报告显示正常
- [ ] 2.2 手动测试：选择昨天日期，验证报告切换到对应日期
- [ ] 2.3 手动测试：选择没有报告数据的日期，验证错误提示正确显示
