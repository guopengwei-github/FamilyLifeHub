## Context

首页 (`page.tsx`) 已经有 `selectedDate` 状态和 `handleDateChange` 函数用于日期导航。日期导航器组件 `DateNavigator` 正确地更新了 `selectedDate`。其他数据卡片（如 SleepCard、ActivityCard）已正确接收并使用 `selectedDate`。

然而，`MorningReport` 和 `EveningReport` 组件没有接收 `date` prop，导致它们始终显示今天的报告。代码注释 "Always show today's reports regardless of selected date" 表明这可能是之前的有意设计，但用户反馈表明这是一个 bug。

## Goals / Non-Goals

**Goals:**
- 修复报告组件的日期绑定，使切换日期后显示对应日期的报告
- 更新错误提示信息，使其更准确（不总是说"今日"）

**Non-Goals:**
- 不修改 API 层（API 已支持 `date` 参数）
- 不添加新的报告类型或功能
- 不修改报告的内容格式

## Decisions

### 1. 传递 `date` prop 给报告组件

**决定**: 在 `page.tsx` 中，将 `format(selectedDate, 'yyyy-MM-dd')` 传递给 `MorningReport` 和 `EveningReport` 组件。

**理由**:
- 报告组件已定义 `date?: string` prop
- 组件内部已正确使用 `date` 参数调用 API
- 这是最小改动方案

### 2. 错误提示信息优化

**决定**: 更新错误提示，从"今日晨间报告尚未生成"改为"晨间报告尚未生成"（去掉"今日"）。

**理由**:
- 避免混淆：当用户查看历史日期时，看到"今日"会感到困惑
- 简洁的提示同样清晰

## Risks / Trade-offs

- **用户体验**: 查看历史日期时可能没有报告数据 → 这是预期行为，错误提示会正确显示
