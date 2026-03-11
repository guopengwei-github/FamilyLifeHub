## Why

首页的晨间报告和晚间复盘报告组件没有接收 `selectedDate` 状态，导致无论用户选择哪个日期，报告始终显示今天的内容。这违背了日期导航器的设计意图——用户切换日期后，所有数据（包括报告）都应切换到对应日期。

## What Changes

- 修复 `MorningReport` 和 `EveningReport` 组件的日期绑定
- 将 `selectedDate` 格式化为 `yyyy-MM-dd` 字符串并传递给两个报告组件
- 更新错误提示信息，从"今日晨间报告尚未生成"改为"该日期的晨间报告尚未生成"等更准确的描述

## Capabilities

### New Capabilities

无新增能力

### Modified Capabilities

无修改能力（这是纯 bug 修复，不涉及 spec 层面的行为变更）

## Impact

- **前端代码**:
  - `frontend/app/page.tsx` - 传递 `date` prop 给报告组件
  - `frontend/components/reports/morning-report.tsx` - 更新错误提示
  - `frontend/components/reports/evening-report.tsx` - 更新错误提示
- **API 调用**: 无变更，API 已支持 `date` 参数
- **用户体验**: 用户切换日期后，报告内容将正确显示对应日期的数据
