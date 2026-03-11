## ADDED Requirements

### Requirement: Reports respect selected date

晨间报告和晚间复盘报告 SHALL 遵循用户选择的日期，显示对应日期的报告内容。

#### Scenario: View report for selected date

- **WHEN** 用户通过日期导航器选择某个日期
- **THEN** 晨间报告和晚间复盘报告 SHALL 请求并显示该日期的报告数据

#### Scenario: Report not found for selected date

- **WHEN** 用户选择的日期没有对应的报告
- **THEN** 系统 SHALL 显示"报告尚未生成"的错误提示（不包含"今日"字样）

#### Scenario: Date change triggers report refresh

- **WHEN** 用户从日期 A 切换到日期 B
- **THEN** 报告组件 SHALL 重新请求日期 B 的报告数据
