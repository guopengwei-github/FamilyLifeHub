# 日期导航器设计文档

**创建日期**: 2024-02-06
**功能**: 多日期查看功能

## 1. 概述

在家庭看板顶部添加日期选择器组件，允许用户查看不同日期的数据。

### 1.1 核心功能

- **前一天/后一天按钮**: 按天切换日期
- **日历按钮**: 弹出式日历选择具体日期
- **今天按钮**: 快速回到当天
- **日期显示**: 显示当前查看的日期（如 "2024年1月31日 星期三"）

### 1.2 用户选择确认

- 日历样式: **弹出式日历**
- 导航行为: **按天切换**
- 默认日期: **今天**
- 无数据日期: **显示空状态**

## 2. 组件设计

### 2.1 新增组件: `DateNavigator`

**位置**: `frontend/components/dashboard/date-navigator.tsx`

**Props 接口**:
```typescript
interface DateNavigatorProps {
  selectedDate: Date;
  onDateChange: (date: Date) => void;
  loading?: boolean;
}
```

**UI 布局**:
```
[←] [2024年1月31日 星期三] [日历图标] [→]     [今天]
```

### 2.2 弹出式日历

- 使用 shadcn/ui 的 `Calendar` 和 `Popover` 组件
- 点击日历图标弹出，选择后自动关闭

### 2.3 修改 `DashboardPage`

- 添加 `selectedDate` 状态
- 修改 `fetchData` 支持可选日期参数
- 将日期传递给 API 调用

## 3. 数据流

```
用户操作 → DateNavigator → onDateChange(date)
→ DashboardPage.fetchData(date) → 后端 API (target_date 参数)
→ 更新所有卡片数据
```

### 3.1 状态管理逻辑

```typescript
const [selectedDate, setSelectedDate] = useState<Date>(new Date());

const fetchData = async (date?: Date) => {
  const targetDate = date || selectedDate;
  const dateStr = format(targetDate, 'yyyy-MM-dd');

  const [summaryData, overviewData] = await Promise.all([
    getDashboardSummary(dateStr),
    getOverview(dateStr),
  ]);
  // ... 更新状态
};

const handleDateChange = (newDate: Date) => {
  setSelectedDate(newDate);
  fetchData(newDate);
};
```

## 4. 空状态与边界情况

| 场景 | 处理方式 |
|------|----------|
| 无数据日期 | 显示空状态提示，不自动跳转 |
| 过去日期 | 不限制，可查看任意历史日期 |
| 未来日期 | 允许查看，显示空状态 |
| 加载状态 | 按钮禁用，显示旋转图标 |
| API 错误 | 复用现有错误处理，可切换日期重试 |

## 5. 实现清单

### 5.1 新建文件

- `frontend/components/dashboard/date-navigator.tsx`

### 5.2 修改文件

- `frontend/app/page.tsx` - 集成日期状态和 DateNavigator
- `frontend/components/dashboard/user-summary-card.tsx` - 空状态处理

### 5.3 依赖项

- `date-fns` - 日期格式化
- shadcn/ui `Calendar` 和 `Popover` 组件

## 6. 可选增强功能

| 功能 | 优先级 |
|------|--------|
| 周视图模式 | 低 |
| 日历标记有数据日期 | 低 |
| 键盘快捷键 | 低 |
| 日期范围对比 | 中 |
