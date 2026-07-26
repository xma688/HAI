# HAI 前端重写设计文档 · "静夜炉边 (Quiet Hearth)"

- 日期：2026-07-23
- 范围：完全重写 `src/hai_avatar/ui/gradio_app.py` 的 HTML 结构与 `src/hai_avatar/ui/styles.css` 全部样式
- 状态：设计定稿，待实现

---

## 1. 背景与目标

### 1.1 现状问题
当前 UI 是一个 Gradio 应用，套了 1342 行自定义 CSS 的深蓝"夜晚陪伴"主题。问题不在概念，而在执行：

- 配色偏**冷蓝**，与暖色品牌插画（暖灯、月亮、少年）气质不符
- 满屏**渐变 + SVG 噪点纹理**，视觉噪音大
- 结构是**长滚动落地页**（hero → 工作区 → story 营销段落 → footer），陪伴产品却应是一屏内的对话空间
- 仍有明显的 **Gradio 默认控件感**
- 字号/间距层级不清，细节不精致

### 1.2 设计目标
1. **暖夜基调**：延续夜晚陪伴情绪，但配色从冷蓝转为暖中性深色，像深夜台灯旁的对话
2. **应用外壳**：从落地页改为一屏内的对话工作台，主体填满视口
3. **富有表现力的暖光**：以琥珀主色 + 月青辅色为核心，允许更大胆的氛围表达——动态暖光、情绪驱动的色温漂移、声波可视化（见 §11）
4. **去 Gradio 味**：气泡、输入框、按钮、进度全部重塑，柔和圆角、克制阴影
5. **交互顺手**：即时反馈、键盘优先、微动效有回应感，操作路径短（见 §12）
6. **可访问**：对比度达标、键盘可达、`prefers-reduced-motion` 兼容

### 1.2.1 设计基调修订（更丰富 / 更大胆 / 更舒服）
在 §2 定义的克制基础上，本次刻意提升"表现力"上限。原则改为：**底子克制，重点大胆**——大面积仍是安静的暖夜，但在少数关键锚点（角色舞台、进度、情绪反馈、发送瞬间）做有记忆点的表达。§11、§12 为新增的加强章节，若与前文的"克制"描述冲突，以 §11/§12 为准。

### 1.3 技术边界（重要）
这是 Gradio 应用，DOM 由 Gradio 框架生成，无法脱离 Gradio 组件模型自由写 HTML。因此"完全重写"的落地方式是：
- 用 `gr.HTML` 注入的自定义 HTML 块（brand/welcome/stage/progress/status 等）全部重写
- `styles.css` 全部重写，包含针对 Gradio 内部类（`.gr-button`、`.wrap`、chatbot 气泡等）的覆盖
- 保持所有 `elem_id`/回调契约不变，避免破坏 `gradio_app.py` 的交互逻辑（除非本文档显式要求调整结构）

不在范围内：后端 pipeline、TTS、Avatar bridge、评测。

---

## 2. 设计语言

### 2.1 配色系统

采用暖中性深色。所有颜色以 CSS 变量定义在 `:root`。

#### 背景层（暖墨，非冷蓝）
| Token | 值 | 用途 |
|-------|-----|------|
| `--bg-base` | `#17140f` | 页面最底色（暖黑墨） |
| `--bg-surface` | `#1f1b15` | 主面板/卡片底 |
| `--bg-raised` | `#28231b` | 悬浮层、输入框、AI 气泡 |
| `--bg-hover` | `#332c22` | hover 态 |

#### 文字层（暖奶白，非灰蓝）
| Token | 值 | 用途 |
|-------|-----|------|
| `--text-strong` | `#f5efe4` | 标题、主文本 |
| `--text` | `#d8d0c2` | 正文 |
| `--text-dim` | `#9a9284` | 次要说明、占位符 |
| `--text-faint` | `#6b6459` | 时间戳、编号 |

#### 主色 / 辅色 / 语义色
| Token | 值 | 用途 |
|-------|-----|------|
| `--amber` | `#e8a34a` | 主强调色（台灯暖光）：主按钮、链接、焦点、用户气泡 |
| `--amber-hover` | `#f0b25f` | 主色 hover |
| `--amber-glow` | `rgba(232,163,74,0.18)` | 主色柔光/半透明底 |
| `--moon` | `#7cc9c4` | 辅色（月青）：仅用于连接状态点、语音波形、微光 |
| `--line` | `rgba(245,239,228,0.08)` | 分隔线、边框（暖白低透明） |
| `--line-strong` | `rgba(245,239,228,0.14)` | 强边框、focus 边 |
| `--ok` | `#83c98a` | 成功 |
| `--warn` | `#e6b45a` | 警告 |
| `--danger` | `#e07a63` | 错误、危险操作 |

#### 原则
- **删除**所有多色渐变和 SVG 噪点纹理背景
- 允许**一处**极淡的径向暖光（页面顶部或角色舞台后方），模拟台灯氛围，透明度 ≤ 0.06
- 阴影用暖黑半透明，克制：`0 1px 2px rgba(0,0,0,.3)` 到 `0 12px 32px rgba(0,0,0,.35)`

### 2.2 字体系统

保留 Google Fonts 引入，收敛为三类角色：

| 角色 | 字体栈 | 用途 |
|------|--------|------|
| 显示/标题 | `"Noto Serif SC", Georgia, serif` | H1/H2 少数标题，带温度感的衬线 |
| 正文/UI | `"Noto Sans SC", -apple-system, "Segoe UI", sans-serif` | 所有正文、按钮、气泡、标签 |
| 等宽 | `"IBM Plex Mono", ui-monospace, monospace` | 仅技术诊断的数字/延迟/provider |

**去掉 Sora**（英文无衬线），减少字体请求。

#### 字号阶梯（rem，root 16px）
| Token | 值 | 行高 | 用途 |
|-------|-----|------|------|
| `--fs-display` | 2.5rem | 1.15 | 欢迎标题 H1 |
| `--fs-h2` | 1.5rem | 1.25 | 区块标题 |
| `--fs-lg` | 1.125rem | 1.5 | 强调正文、气泡 |
| `--fs-base` | 1rem | 1.6 | 正文 |
| `--fs-sm` | 0.875rem | 1.5 | 次要、标签 |
| `--fs-xs` | 0.75rem | 1.4 | 编号、时间戳、诊断 |

字重：正文 400，中强调 500，标题 600/700。字距：等宽小标签 `letter-spacing: 0.08em` 大写化。

### 2.3 间距 / 圆角 / 层级

#### 间距（4px 基准）
`--space-1: 4px` … `--space-2: 8px`、`3: 12px`、`4: 16px`、`5: 24px`、`6: 32px`、`8: 48px`、`10: 64px`

#### 圆角
| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | 8px | 小标签、状态点容器 |
| `--radius-md` | 12px | 按钮、输入框 |
| `--radius-lg` | 16px | 气泡、卡片 |
| `--radius-xl` | 24px | 主面板、舞台 |
| `--radius-full` | 999px | 圆形按钮、状态点 |

#### 阴影
`--shadow-sm`、`--shadow-md`、`--shadow-lg`（见 2.1 原则），全部暖黑半透明、无彩色投影。

#### 布局尺寸
- 内容最大宽 `--page-width: 1200px`，居中
- 主工作区在桌面为左右双栏：Live2D 舞台与对话区各占约一半（`minmax` 网格），间距 `--space-6`
- 断点：`≤ 960px` 单列堆叠

---

## 3. 布局架构

### 3.1 整体结构（从上到下）
```
┌────────────────────────────────────────────────┐
│ Header  [H · HAI 安静的AI陪伴]        [● 状态]   │  极简顶栏，sticky
├────────────────────────────────────────────────┤
│                                                  │
│  ┌── 角色舞台 ──────┐   ┌── 对话区 ──────────┐  │
│  │                  │   │ 对话标题 + 隐私提示 │  │
│  │   Live2D iframe  │   │ ┌─ 进度呼吸条 ─┐   │  │
│  │   / 未连接占位    │   │ │              │   │  │
│  │                  │   │ ├─ 消息气泡流 ─┤   │  │
│  │  暖光氛围底       │   │ │  user/ai     │   │  │
│  │                  │   │ │              │   │  │
│  │  舞台字幕         │   │ ├─ 输入框+发送 ┤   │  │
│  │                  │   │ ├─ 快捷话题    ┤   │  │
│  └──────────────────┘   │ ├─ 语音输入(折叠)┤ │  │
│                          │ └─ 清空 按钮   ┘   │  │
│                          └────────────────────┘  │
│                                                  │
│  ▸ 本轮表现 · 技术诊断 (Accordion，默认折叠)      │
└────────────────────────────────────────────────┘
```

### 3.2 关键改动 vs 现状
- **删除** hero 长欢迎区独立成屏：欢迎语精简为对话区顶部一句轻文案，不再是占满首屏的营销 hero
- **删除** `_story_markup()` 整个 story 营销段落 + footer 大区块（改为 header 内极小版权，或直接去掉）
- 工作区**填满视口高度**（`min-height: calc(100dvh - header)`），而非往下滚动才看到
- 双栏比例从 `scale=6:6` 保持约 1:1，但用 CSS Grid 控制而非依赖 Gradio scale
- 技术诊断保留为折叠 Accordion，收在底部

### 3.3 各区块设计

#### Header（顶栏）
- sticky 顶部，高度约 64px，`--bg-surface` + 底部 `--line` 分隔
- 左：品牌标记（圆角方块内暖白"H" + 暖光底）+ "HAI / 安静的 AI 陪伴"（主副两行）
- 右：连接状态 chip（月青点=已连接 prometheus / 暗点=演示模式），文字小号
- 去掉"本轮表现"锚点链接（信息已在底部 Accordion）

#### 角色舞台（左栏）
- `--radius-xl` 大圆角面板，`--bg-surface` 底
- 面板头：小标签 "Companion" + "Live2D Avatar" + 右侧状态
- 主体：prometheus 时嵌 iframe；否则显示优雅的未连接占位（月相图标 + "请启用真实角色模式"）
- 舞台后方一处极淡径向暖光（台灯感）
- 底部字幕："我在，慢慢说。" + "表情 · 动作 · 口型"

#### 对话区（右栏）
- 面板头："Conversation / 我们的对话" + 右侧"短期上下文已开启"隐私提示 chip
- **进度呼吸条**：替换现在的六格网格。做成单行安静的状态条——一个呼吸的圆点 + 当前阶段文案（理解/回复/声音/表演/完成），阶段推进用一条细进度线，不铺满格子
- **消息气泡**：
  - 用户气泡：右对齐，`--amber-glow` 暖底 + `--text-strong`，`--radius-lg`（右下角略收）
  - AI 气泡：左对齐，`--bg-raised` 底，`--radius-lg`（左下角略收）
  - 气泡浮现动效（淡入 + 轻微上移 8px）
  - 覆盖 Gradio chatbot 内部样式，去掉默认边框/头像块感
- **输入区**：`--bg-raised` 圆角输入框（`--radius-md`），focus 时 `--amber` 边 + 柔光；右侧主按钮"发送"（琥珀实心）
- **快捷话题**：3 个 pill 按钮（幽灵态：透明底 + `--line` 边，hover 提亮）
- **语音输入**：折叠 Accordion，内嵌麦克风组件
- **清空**：次要幽灵按钮，触发确认对话框（保留现有 clear-dialog 逻辑，重塑样式）

#### 技术诊断（底部 Accordion）
- 默认折叠，标题"本轮表现 · 技术诊断"
- 展开显示：runtime 行（LLM/TTS/Avatar provider，等宽小字）+ 状态网格（Emotion/Expression/Gesture/Voice/Intensity/Latency）
- 状态网格重塑为紧凑卡片，每格：小标签(dim) + 值(strong)

---

## 4. 组件规格

### 4.1 按钮
| 类型 | 样式 | 用途 |
|------|------|------|
| Primary | 琥珀实心 `--amber`，深色文字，`--radius-md`，hover 提亮+轻微上浮 | 发送 |
| Ghost | 透明底 + `--line` 边，`--text`，hover `--bg-hover` | 快捷话题、清空、取消 |
| Danger | `--danger` 实心或描边 | 确认清空 |

- 高度：常规 40px，小号（sm）32px
- 内边距：`0 --space-4`
- 过渡：`background/transform 160ms ease`
- focus-visible：`--amber` 2px outline，offset 2px

### 4.2 输入框
- `--bg-raised` 底，`--line` 边，`--radius-md`，内边距 `--space-3`
- placeholder 用 `--text-dim`
- focus：边框转 `--amber`，外发 `0 0 0 3px --amber-glow`
- textarea 2 行起，最多 5 行自增

### 4.3 状态 chip
- 圆角 `--radius-full`，内小圆点 + 文字小号
- 已连接：月青点（可呼吸微动）；演示：`--text-faint` 静态点

### 4.4 进度呼吸条
- 单行容器：左呼吸圆点（`--amber`，`prefers-reduced-motion` 时停止）+ 阶段文案 + 右侧细进度线
- 阶段：理解 → 回复 → 声音 → 表演 → 完成
- 错误态：圆点转 `--danger`，文案"这轮回应没有完成，可重新发送"

### 4.5 气泡
- 见 3.3 对话区。最大宽度 78% 容器，`--fs-lg` 行高 1.5
- 连续同角色消息间距收窄

### 4.6 确认对话框
- 居中浮层 + 半透明遮罩（`rgba(0,0,0,.5)`）
- 卡片：`--bg-raised`，`--radius-xl`，`--shadow-lg`
- 标题 + 说明 + 取消(Ghost)/确认清空(Danger)

---

## 5. 动效与交互

- **全局过渡**：颜色/变换 160ms ease，避免大幅位移
- **气泡浮现**：`opacity 0→1` + `translateY 8px→0`，240ms
- **呼吸点**：`scale/opacity` 循环 2s，仅状态点与进度点
- **舞台暖光**：静态径向渐变，不动画
- **`prefers-reduced-motion: reduce`**：关闭所有循环动画与浮现位移，仅保留即时状态切换
- **hover**：按钮/pill 轻微提亮，主按钮 `translateY(-1px)`
- **focus-visible**：所有可交互元素统一琥珀 outline

---

## 6. 响应式

| 断点 | 行为 |
|------|------|
| `> 960px` | 双栏网格，舞台与对话各半，工作区填满视口 |
| `≤ 960px` | 单列堆叠：舞台在上（限高，如 40vh）、对话在下 |
| `≤ 560px` | 内边距收窄至 `--space-4`，字号 display 降一档，快捷话题可横向滚动 |

- 内边距：桌面 `--space-8`，移动 `--space-4`
- 触摸目标 ≥ 44px

---

## 7. 可访问性

- 文字/背景对比度：正文 ≥ 4.5:1，大字 ≥ 3:1（`--text` on `--bg-surface` 已满足）
- 所有交互元素键盘可达，`:focus-visible` 明确
- 状态用文字+颜色双编码，不仅靠颜色
- `aria-live` 保留在进度与通知区
- `prefers-reduced-motion` 兼容
- 图标为装饰性时 `aria-hidden`

---

## 8. 实现约束与契约

为不破坏 `gradio_app.py` 的回调，实现时遵守：

1. 保留所有现有 `elem_id`（`brand-header`、`welcome-section`、`experience-shell`、`workspace`、`avatar-panel`、`chat-panel`、`conversation`、`message-input`、`send-button`、`quick-prompts`、`voice-tools`、`voice-input`、`reply-audio`、`turn-warnings`、`conversation-actions`、`clear-button`、`turn-details`、`clear-dialog` 等）——若需新增/调整，需同步更新 `gradio_app.py` 且保证回调 outputs 对应
2. 保留 HTML 生成函数的**签名与返回契约**（`_brand_header`、`_welcome_markup`、`_avatar_stage_markup`、`_conversation_heading`、`_progress_html`、`_initial_status`、`_format_status_with_latency`、`_notice`），重写其内部 HTML；**删除** `_story_markup`（连同 `story-section` 输出）
   - `welcome_section`（`gradio_app.py:281`）当前是 respond 回调的一个 output slot，发送时被设为 `visible=False` 以收起首屏 hero。重写后 `_welcome_markup` 改为对话区顶部的一句轻欢迎文案；**保留该 output slot 与 `visible=False` 行为**（发送后淡出欢迎语），不改动 send_outputs 列表长度与顺序，避免破坏生成器 yield 的元组对齐
3. `_progress_html` 的 stage 取值（understanding/reply/voice/performance/complete/error）与 `_PROGRESS_STAGES` 保持一致，供 respond 生成器调用
4. CSS 类名统一用 `hai-` 前缀，避免与 Gradio 冲突；对 Gradio 内部类的覆盖集中成一节并加注释
5. 现有测试 `tests/` 不直接断言 UI HTML；实现后运行 `PYTHONPATH=src pytest` 确认无回归，并手动启动 `scripts/run_gradio.py` 目视验证

---

## 9. 交付物

1. 重写后的 `src/hai_avatar/ui/gradio_app.py`（结构 + HTML 函数）
2. 重写后的 `src/hai_avatar/ui/styles.css`
3. 手动启动截图/目视验证：mock 模式与 prometheus 模式各一次
4. `pytest` 全绿

---

## 10. 非目标（YAGNI）

- 不引入前端构建工具/框架（保持纯 Gradio + CSS）
- 不做浅色主题切换（仅暖夜暗色）
- 不改动后端、评测、TTS、Avatar 逻辑
- 不新增营销页面内容

---

## 11. 丰富度与大胆度（Enhancement）

目标：在安静的暖夜底子上，用少数高表现力锚点制造记忆点。全部纯 CSS + 少量内联 SVG，无新依赖。所有效果都遵守 `prefers-reduced-motion`（reduce 时退化为静态）。

### 11.1 活的暖光背景（Living Ambient Light）
- 页面底层放一处**缓慢漂移的径向暖光**（琥珀），像台灯在呼吸。透明度峰值 ≤ 0.10，周期 ~12s，位移极小（几十 px），`will-change` 控制在单层
- 角色舞台后方叠加第二处更聚焦的暖光，强化"炉边"焦点
- reduce 模式：固定为静态径向渐变

### 11.2 情绪驱动的色温（Emotion-reactive Accent）
- 根据本轮 `avatar_command.emotion` 给 `#experience-shell` 打一个 `data-emotion` 属性，CSS 用属性选择器微调强调色调：
  - happy/supportive → 暖光更亮更金
  - thoughtful/serious → 暖光收敛、偏冷一度
  - apologetic/confused → 降饱和
- 仅影响暖光与状态点色相，**不影响文字对比度**（正文色始终不变，保证可读）
- 实现：`respond` 完成时通过一个 `gr.HTML`/属性更新写入 `data-emotion`；若实现成本高则降级为仅进度条颜色随情绪变化（写入设计但标注"可选增强"）

### 11.3 声波可视化（Voice Waveform）
- 呼应品牌插画里的声波线。当本轮有音频（`audio_available=true`）时，在角色舞台底部字幕上方显示一条**月青声波**：5–7 根竖条做高度错相位起伏（纯 CSS animation），营造"正在说话"感
- 无音频/静止时波形压平为一条细线
- reduce 模式：静态等高细条

### 11.4 更立体的气泡与层次
- AI 气泡：`--bg-raised` + 顶部 1px 高光内描边（`inset 0 1px 0 rgba(255,255,255,.04)`）+ `--shadow-md`，营造"浮起"感
- 用户气泡：`--amber-glow` 底 + 琥珀细边（`1px --amber` 30% 透明），气泡右侧带一抹更暖的渐隐
- 气泡入场：淡入 + 上移 + 极轻微缩放（`scale .98→1`），弹性缓动 `cubic-bezier(.2,.8,.2,1)`

### 11.5 品牌标记升级
- Header 的"H"标记做成**发光徽标**：圆角方块 + 内暖光 + hover 时暖光扩散
- 连接状态点用双层圆环（月青核心 + 外扩呼吸环），比单点更有生命感

### 11.6 首屏进场编排（Staggered Reveal）
- 页面加载时，header → 舞台 → 对话区依次淡入（stagger 各 ~80ms），一次性的入场动画，营造精致的第一印象
- reduce 模式：全部立即显示

---

## 12. 交互舒适度（Interaction Comfort）

目标：反馈即时、路径短、键盘优先、错误不打断。以下多为 `gradio_app.py` 行为与 CSS 状态的配合。

### 12.1 输入与发送
- **Enter 发送 / Shift+Enter 换行**：沿用 Gradio Textbox 的 submit（已支持），文档明确该约定并在输入框下方用极小提示文字标注
- **发送中禁用态**：按钮变"回应中…"并禁用（现有逻辑保留），加一个**内联 spinner**（呼吸点）替代纯文字，视觉上更"活"
- **输入框自动聚焦**：页面加载后焦点落在输入框；发送完成后焦点回到输入框，连续对话不用点鼠标
- **发送成功微反馈**：发送瞬间输入框做一次极轻的"塌陷"动画（scale 0.99 回弹），给出触发确认感

### 12.2 快捷话题
- 点击 pill 后**直接发送**（而非仅填入输入框），减少一步；或保留填入但视觉上更明确可点。**决策：直接填入并自动聚焦输入框末尾**，让用户可微调后发送（更安全，避免误触即发）
- pill hover：提亮 + 轻微上浮；有 `title` 说明

### 12.3 进度反馈
- 进度呼吸条实时反映五阶段（理解/回复/声音/表演/完成），当前阶段文案 + 呼吸点 + 细进度线推进
- **回复文字先到先显示**：`reply` 阶段就把 AI 气泡插入（现有生成器已支持），后续声音/表演阶段继续在进度条推进，让用户尽早看到文字

### 12.4 消息区
- **自动滚动到底**：新消息插入后滚到底部（Gradio chatbot 默认行为，确认保留）
- **复制按钮**：保留 chatbot 的 copy，样式重塑为 hover 出现的幽灵图标
- 长回复不截断视觉，气泡内滚动由页面滚动承接

### 12.5 语音输入
- 折叠区标题更明确："🎙 语音输入（录完自动转文字）"（不使用 emoji，改用内联 SVG 麦克风图标 + 文案）
- 录音中状态可视化（若 Gradio 组件支持，加 CSS 呼吸边）

### 12.6 错误与降级
- 通知区（`turn-warnings`）样式重塑：警告=暖黄描边卡片，错误=珊瑚红描边卡片，均带小图标，`aria-live` 保留
- TTS 失败等非致命降级：文案强调"文字/表情正常，仅本轮语音不可用"，不显示为红色错误，用中性提示样式，避免惊吓

### 12.7 清空确认
- 确认对话框保留，重塑为居中浮层 + 遮罩，**Esc 关闭 / 点击遮罩关闭**（若可用 Gradio 事件实现则实现，否则至少取消按钮聚焦友好）

### 12.8 交互性能与降级标注
- 所有增强按"渐进增强"实现：CSS 动效失败不影响功能；`data-emotion`、Esc 关闭等若增加 `gradio_app.py` 复杂度过高，标注为"可选增强"，核心交互（发送/进度/清空/语音）必须稳定
- 明确优先级：**P0** 输入自动聚焦、Enter 发送、进度即时、错误友好；**P1** 情绪色温、声波、进场编排、Esc 关闭
