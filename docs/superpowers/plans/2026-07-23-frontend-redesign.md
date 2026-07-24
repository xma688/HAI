# HAI 前端重写实现计划 · "静夜炉边 (Quiet Hearth)"

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `docs/superpowers/specs/2026-07-23-frontend-redesign-design.md` 完全重写 Gradio 前端的 HTML 结构与全部 CSS，得到暖夜、富表现力、交互顺手的对话工作台。

**Architecture:** 纯 Gradio + 手写 CSS，无前端构建工具。重写 `gradio_app.py` 中所有 `gr.HTML` 生成函数与 Blocks 结构，全量重写 `styles.css`。对可断言的 HTML 生成函数用 TDD（pytest 字符串断言），对纯视觉部分用手动启动目视验证。分层交付：先契约与 HTML 函数（可测），再 CSS 骨架，再富表现力增强，最后交互行为与目视验证。

**Tech Stack:** Python 3.11+, Gradio, Pydantic, pytest, 纯 CSS3（含 CSS 变量、Grid、动画、`prefers-reduced-motion`）。字体：Noto Serif SC / Noto Sans SC / IBM Plex Mono（Google Fonts）。

## Global Constraints

- 不引入前端构建工具/框架，保持纯 Gradio + CSS。
- 不改动后端 pipeline、TTS、Avatar bridge、评测逻辑。
- CSS 类名统一 `hai-` 前缀；对 Gradio 内部类的覆盖集中到 CSS 末尾一节并加注释。
- 保留所有现有 `elem_id`；`send_outputs` 列表的长度与顺序不得改变（8 个 output，见 Task 1 契约），否则破坏 respond 生成器的 yield 元组对齐。
- `_progress_html` 的 stage 取值必须是 `understanding` / `reply` / `voice` / `performance` / `complete` / `error`，与 `_PROGRESS_STAGES`（4 元组：understanding/reply/voice/performance）一致。
- 所有动效遵守 `prefers-reduced-motion: reduce`（退化为静态/即时）。
- 配色/字体/圆角/间距 token 严格采用 spec §2 定义的值。
- 每个任务结束运行 `PYTHONPATH=src pytest` 确认无回归。
- P0 交互（发送 / 进度即时 / 清空 / 语音 / 错误友好）必须稳定；P1 增强（情绪色温 / 声波 / 进场编排 / Esc 关闭）失败时可降级但不得影响 P0。

---

### Task 1: 建立可测试的 HTML 生成函数基线与测试脚手架

**Files:**
- Create: `tests/test_gradio_html.py`
- Modify: `src/hai_avatar/ui/gradio_app.py`（`_progress_html`、`_notice`、`_format_status_with_latency`、`_initial_status`）

**Interfaces:**
- Consumes: `hai_avatar.schemas.AvatarCommand`、`EmotionType`、`ExpressionType`、`GestureType`、`VoiceStyleType`
- Produces:
  - `_progress_html(stage: str = "idle") -> str`：返回含 `hai-progress` 根类的 HTML；错误态含 `is-error`；complete 态所有步骤含 `done`
  - `_notice(message: str, *, error: bool = False) -> str`：error=True 时含 `hai-notice error`，且消息经 `html.escape`
  - `_format_status_with_latency(cmd: AvatarCommand, latency_ms: float | None) -> str`：返回含 `hai-status-grid` 的 6 格 HTML
  - `_initial_status() -> str`：返回含 `hai-status-grid` 的初始 6 格

- [ ] **Step 1: 写失败测试**

创建 `tests/test_gradio_html.py`：

```python
from hai_avatar.schemas import (
    AvatarCommand,
    EmotionType,
    ExpressionType,
    GestureType,
    VoiceStyleType,
)
from hai_avatar.ui import gradio_app


def test_progress_idle_has_root_class():
    html = gradio_app._progress_html("idle")
    assert "hai-progress" in html
    assert 'role="status"' in html


def test_progress_error_marks_error_state():
    html = gradio_app._progress_html("error")
    assert "is-error" in html


def test_progress_complete_marks_all_done():
    html = gradio_app._progress_html("complete")
    # 4 个阶段步骤，complete 时全部 done
    assert html.count("done") >= 4


def test_notice_escapes_and_marks_error():
    html = gradio_app._notice("<script>x</script>", error=True)
    assert "hai-notice error" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_status_grid_renders_six_cells():
    cmd = AvatarCommand(
        emotion=EmotionType.happy,
        expression=ExpressionType.smile,
        gestures=[GestureType.nod],
        voice_style=VoiceStyleType.cheerful,
        gesture_intensity=0.6,
        speaking_rate=1.05,
    )
    html = gradio_app._format_status_with_latency(cmd, 1234.0)
    assert "hai-status-grid" in html
    assert html.count("hai-status-item") == 6
    assert "1.2s" in html  # latency 格式化


def test_initial_status_renders_grid():
    html = gradio_app._initial_status()
    assert "hai-status-grid" in html
    assert html.count("hai-status-item") == 6
```

- [ ] **Step 2: 运行测试确认失败或通过**

Run: `PYTHONPATH=src pytest tests/test_gradio_html.py -v`
Expected: 大部分 PASS（这些函数已存在且行为已匹配），若有 FAIL 说明当前实现与断言不符——本步骤目的是锁定契约基线。如全部 PASS，直接进入 Step 3 提交基线。

- [ ] **Step 3: 若有失败，最小修正 `gradio_app.py` 使断言通过**

仅在 Step 2 出现 FAIL 时执行：调整对应函数使其满足上述类名/转义/格子数契约。不做视觉改动，只保证契约。

- [ ] **Step 4: 运行全量测试**

Run: `PYTHONPATH=src pytest`
Expected: PASS（原有测试 + 新增 6 条）

- [ ] **Step 5: 提交**

```bash
git add tests/test_gradio_html.py src/hai_avatar/ui/gradio_app.py
git commit -m "test: lock html-generator contracts before redesign"
```

---

### Task 2: 重写 Blocks 结构与 HTML 生成函数（暖夜应用外壳）

**Files:**
- Modify: `src/hai_avatar/ui/gradio_app.py`（`_brand_header`、`_welcome_markup`、`_avatar_stage_markup`、`_conversation_heading`、`_progress_html`、`create_interface`；删除 `_story_markup`）
- Test: `tests/test_gradio_html.py`

**Interfaces:**
- Consumes: Task 1 的 6 条契约测试
- Produces:
  - `_brand_header(avatar_provider: str) -> str`：含 `hai-header` 根类、品牌标记、连接状态 chip（`connected`/`demo`）
  - `_welcome_markup() -> str`：改为对话区顶部轻欢迎语，含 `hai-welcome` 根类（不再是占满首屏的 hero）
  - `_avatar_stage_markup(settings: Settings) -> str`：含 `hai-avatar-stage`，prometheus 时嵌 iframe（保留现有 bridge_url 逻辑），否则未连接占位
  - `_conversation_heading() -> str`：含 `hai-conversation-heading`
  - `_progress_html`：改为单行呼吸条结构（`hai-progress` + `hai-progress-dot` + `hai-progress-track`），阶段文案不变
  - `create_interface`：删除 story-section 输出；`send_outputs` 保持 8 项顺序不变：`[chatbot, progress_output, avatar_status, warnings_output, audio_output, welcome_section, send_btn, user_input]`

- [ ] **Step 1: 更新测试以覆盖新结构**

在 `tests/test_gradio_html.py` 追加：

```python
def test_brand_header_connected_vs_demo():
    connected = gradio_app._brand_header("prometheus")
    demo = gradio_app._brand_header("mock")
    assert "hai-header" in connected
    assert "connected" in connected
    assert "demo" in demo


def test_welcome_is_lightweight_greeting():
    html = gradio_app._welcome_markup()
    assert "hai-welcome" in html


def test_story_markup_removed():
    assert not hasattr(gradio_app, "_story_markup")


def test_progress_breathing_bar_structure():
    html = gradio_app._progress_html("voice")
    assert "hai-progress" in html
    assert "hai-progress-dot" in html
    assert "hai-progress-track" in html
```

- [ ] **Step 2: 运行确认失败**

Run: `PYTHONPATH=src pytest tests/test_gradio_html.py -k "brand_header or welcome_is or story_markup or breathing" -v`
Expected: FAIL（新结构尚未实现，`_story_markup` 仍存在）

- [ ] **Step 3: 重写 HTML 生成函数**

在 `gradio_app.py` 中：

1. `_brand_header` 改为（保留签名）：

```python
def _brand_header(avatar_provider: str) -> str:
    connected = avatar_provider == "prometheus"
    status_class = "connected" if connected else "demo"
    status_text = "角色已连接" if connected else "演示模式"
    return f"""
    <header class="hai-header" role="banner">
      <div class="hai-brand">
        <span class="hai-brand-mark" aria-hidden="true">H</span>
        <span class="hai-brand-copy"><b>HAI</b><small>安静的 AI 陪伴</small></span>
      </div>
      <span class="hai-status-chip {status_class}"><i class="hai-dot" aria-hidden="true"></i>{status_text}</span>
    </header>
    """
```

2. `_welcome_markup` 改为轻欢迎语（保留签名，去掉背景图 hero 逻辑）：

```python
def _welcome_markup() -> str:
    return """
    <div id="hai-welcome" class="hai-welcome">
      <span class="hai-welcome-eyebrow">Emotion-aware companion</span>
      <p class="hai-welcome-line">今晚想说什么，<em>我在听。</em></p>
    </div>
    """
```

3. `_avatar_stage_markup`（保留现有 bridge_url 计算，仅重塑 HTML 类名）：

```python
def _avatar_stage_markup(settings: Settings) -> str:
    if settings.avatar.provider == "prometheus":
        bridge_host = settings.avatar.bridge_host
        browser_host = "127.0.0.1" if bridge_host == "0.0.0.0" else bridge_host
        bridge_url = f"http://{browser_host}:{settings.avatar.bridge_port}/?embed=1"
        content = (
            f'<iframe title="HAI Live2D 虚拟角色" src="{bridge_url}" allow="autoplay"></iframe>'
        )
        mode = "live"
        state = "Live2D · 已连接"
    else:
        content = (
            '<div class="hai-stage-empty"><span class="hai-stage-moon" aria-hidden="true">☾</span>'
            '<span>Live2D Avatar</span><small>请启用真实角色模式</small></div>'
        )
        mode = "static"
        state = "Avatar · 未连接"
    return f"""
    <div class="hai-panel-head">
      <div class="hai-panel-title"><span>Companion</span><strong>Live2D Avatar</strong></div>
      <span class="hai-stage-state">{state}</span>
    </div>
    <div id="avatar-stage" class="hai-avatar-stage {mode}">
      <div class="hai-stage-glow" aria-hidden="true"></div>
      {content}
      <div class="hai-waveform {mode}" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <div class="hai-stage-caption"><span>我在，慢慢说。</span><small>表情 · 动作 · 口型</small></div>
    </div>
    """
```

4. `_conversation_heading`：

```python
def _conversation_heading() -> str:
    return """
    <div class="hai-panel-head hai-conversation-heading">
      <div class="hai-panel-title"><span>Conversation</span><strong>我们的对话</strong></div>
      <span class="hai-privacy-chip">短期上下文已开启</span>
    </div>
    """
```

5. `_progress_html` 改为呼吸条（保留 stage 取值语义）：

```python
def _progress_html(stage: str = "idle") -> str:
    if stage == "error":
        return (
            '<div class="hai-progress is-error" role="status" aria-live="polite" aria-busy="false">'
            '<span class="hai-progress-dot" aria-hidden="true"></span>'
            '<div class="hai-progress-copy"><b>这轮回应没有完成</b>'
            '<span>你的输入仍然保留，可以重新发送。</span></div>'
            '<div class="hai-progress-track"><i style="width:100%"></i></div></div>'
        )
    stage_names = [name for name, _, _ in _PROGRESS_STAGES]
    current_index = stage_names.index(stage) if stage in stage_names else -1
    is_complete = stage == "complete"
    total = len(_PROGRESS_STAGES)
    if is_complete:
        message = "这轮回应已经完成"
        done_labels = [label for _, label, _ in _PROGRESS_STAGES]
        percent = 100
    elif current_index >= 0:
        message = _PROGRESS_STAGES[current_index][2]
        done_labels = [label for _, label, _ in _PROGRESS_STAGES[: current_index + 1]]
        percent = int((current_index + 1) / total * 100)
    else:
        message = "准备好听你说"
        done_labels = []
        percent = 0
    busy = "true" if current_index >= 0 and not is_complete else "false"
    # done 标记：complete 或已完成阶段用于测试断言与视觉
    done_markup = "".join(f'<span class="done">{label}</span>' for label in done_labels)
    return f"""
    <div class="hai-progress" role="status" aria-live="polite" aria-busy="{busy}">
      <span class="hai-progress-dot" aria-hidden="true"></span>
      <div class="hai-progress-copy"><b>{message}</b><span class="hai-progress-stages">{done_markup}</span></div>
      <div class="hai-progress-track"><i style="width:{percent}%"></i></div>
    </div>
    """
```

6. 删除 `_story_markup` 函数定义。

7. 在 `create_interface` 中：删除 `gr.HTML(_story_markup(), elem_id="story-section")` 那一行；确认 `send_outputs` 仍为 8 项且顺序不变；`welcome_section` 仍作为第 6 个 output 且发送时 `gr.update(visible=False)` 行为保留。

- [ ] **Step 4: 运行测试确认通过**

Run: `PYTHONPATH=src pytest tests/test_gradio_html.py -v`
Expected: PASS（含 `test_story_markup_removed`、`test_progress_complete_marks_all_done` 仍需 ≥4 个 `done`——新 `_progress_html` complete 时输出 4 个 `class="done"` span，满足）

- [ ] **Step 5: 运行全量测试并提交**

Run: `PYTHONPATH=src pytest`
Expected: PASS

```bash
git add src/hai_avatar/ui/gradio_app.py tests/test_gradio_html.py
git commit -m "feat: rewrite gradio html structure to app-shell layout"
```

---

### Task 3: 全量重写 styles.css —— token 系统 + 布局骨架

**Files:**
- Modify: `src/hai_avatar/ui/styles.css`（整文件替换）

**Interfaces:**
- Consumes: Task 2 的类名（`hai-header`、`hai-welcome`、`hai-panel-head`、`hai-avatar-stage`、`hai-progress`、`hai-status-grid`、`hai-conversation-heading` 等）与 `elem_id`（`experience-shell`、`workspace`、`avatar-panel`、`chat-panel`）
- Produces: 一套 `:root` token（spec §2）+ 应用外壳布局（header + 双栏 grid），此为后续 Task 4/5 的样式基座

- [ ] **Step 1: 替换 styles.css 头部——字体引入 + token**

用 spec §2 的值重写文件开头：

```css
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+SC:wght@400;500;600&family=Noto+Serif+SC:wght@600;700&display=swap");

:root {
  color-scheme: dark;
  /* 背景 */
  --bg-base: #17140f;
  --bg-surface: #1f1b15;
  --bg-raised: #28231b;
  --bg-hover: #332c22;
  /* 文字 */
  --text-strong: #f5efe4;
  --text: #d8d0c2;
  --text-dim: #9a9284;
  --text-faint: #6b6459;
  /* 主/辅/语义 */
  --amber: #e8a34a;
  --amber-hover: #f0b25f;
  --amber-glow: rgba(232,163,74,0.18);
  --moon: #7cc9c4;
  --line: rgba(245,239,228,0.08);
  --line-strong: rgba(245,239,228,0.14);
  --ok: #83c98a;
  --warn: #e6b45a;
  --danger: #e07a63;
  /* 间距 */
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
  --space-5:24px; --space-6:32px; --space-8:48px; --space-10:64px;
  /* 圆角 */
  --radius-sm:8px; --radius-md:12px; --radius-lg:16px; --radius-xl:24px; --radius-full:999px;
  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0,0,0,.30);
  --shadow-md: 0 6px 18px rgba(0,0,0,.32);
  --shadow-lg: 0 12px 32px rgba(0,0,0,.35);
  /* 字号 */
  --fs-display:2.5rem; --fs-h2:1.5rem; --fs-lg:1.125rem;
  --fs-base:1rem; --fs-sm:.875rem; --fs-xs:.75rem;
  --page-width:1200px;
  --font-display:"Noto Serif SC", Georgia, serif;
  --font-body:"Noto Sans SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono:"IBM Plex Mono", ui-monospace, monospace;
}
```

- [ ] **Step 2: 全局重置 + 页面容器（暖夜底，无渐变无噪点）**

```css
html { scroll-behavior: smooth; background: var(--bg-base) !important; }
body { margin:0; overflow-x:hidden; background: var(--bg-base) !important; }
body, .gradio-container {
  color: var(--text) !important;
  font-family: var(--font-body) !important;
  font-size: var(--fs-base);
  line-height: 1.6;
}
.gradio-container {
  max-width:none !important; min-height:100dvh !important;
  padding:0 !important; background: var(--bg-base) !important;
}
.gradio-container main, .gradio-container .main {
  width:100% !important; max-width:none !important; padding:0 !important;
}
footer, .footer { display:none !important; }
a, button, textarea, summary { -webkit-tap-highlight-color: transparent; }
:focus-visible { outline:2px solid var(--amber) !important; outline-offset:2px !important; }
/* 内容居中容器 */
#brand-header, #experience-shell {
  width:min(100%, var(--page-width)) !important;
  margin-inline:auto !important;
}
```

- [ ] **Step 3: Header 布局**

```css
.hai-header {
  display:flex; align-items:center; justify-content:space-between;
  gap:var(--space-4); padding:var(--space-3) var(--space-6);
  position:sticky; top:0; z-index:20;
  background:color-mix(in srgb, var(--bg-surface) 92%, transparent);
  backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line);
}
.hai-brand { display:flex; align-items:center; gap:var(--space-3); }
.hai-brand-mark {
  width:36px; height:36px; border-radius:var(--radius-md);
  display:grid; place-items:center; font-weight:700; color:var(--bg-base);
  background:linear-gradient(135deg, var(--amber), var(--amber-hover));
  box-shadow:0 0 18px var(--amber-glow);
}
.hai-brand-copy { display:flex; flex-direction:column; line-height:1.1; }
.hai-brand-copy b { color:var(--text-strong); font-size:var(--fs-lg); }
.hai-brand-copy small { color:var(--text-dim); font-size:var(--fs-xs); }
.hai-status-chip {
  display:inline-flex; align-items:center; gap:var(--space-2);
  padding:var(--space-1) var(--space-3); border-radius:var(--radius-full);
  border:1px solid var(--line); font-size:var(--fs-sm); color:var(--text-dim);
}
.hai-status-chip .hai-dot { width:8px; height:8px; border-radius:50%; background:var(--text-faint); }
.hai-status-chip.connected { color:var(--text); }
.hai-status-chip.connected .hai-dot { background:var(--moon); box-shadow:0 0 8px var(--moon); }
```

- [ ] **Step 4: 双栏工作区 grid**

```css
#experience-shell { padding:var(--space-6) var(--space-6) var(--space-8); }
.hai-welcome { text-align:center; margin-bottom:var(--space-5); }
.hai-welcome-eyebrow {
  font-size:var(--fs-xs); letter-spacing:.14em; text-transform:uppercase;
  color:var(--amber); display:inline-block; margin-bottom:var(--space-2);
}
.hai-welcome-line { font-family:var(--font-display); font-size:var(--fs-h2); color:var(--text-strong); margin:0; }
.hai-welcome-line em { color:var(--amber); font-style:normal; }
#workspace {
  display:grid !important; grid-template-columns:1fr 1fr; gap:var(--space-6);
  align-items:stretch; min-height:calc(100dvh - 220px);
}
#avatar-panel, #chat-panel {
  display:flex; flex-direction:column; gap:var(--space-4);
  background:var(--bg-surface); border:1px solid var(--line);
  border-radius:var(--radius-xl); padding:var(--space-5); box-shadow:var(--shadow-md);
}
.hai-panel-head { display:flex; align-items:center; justify-content:space-between; }
.hai-panel-title { display:flex; flex-direction:column; }
.hai-panel-title span { font-size:var(--fs-xs); letter-spacing:.1em; text-transform:uppercase; color:var(--text-dim); }
.hai-panel-title strong { font-size:var(--fs-lg); color:var(--text-strong); }
```

- [ ] **Step 5: 目视验证（mock）**

Run: `PYTHONPATH=src python scripts/run_gradio.py`
在浏览器打开 `http://127.0.0.1:7860`，确认：header 暖夜风、双栏并排、无冷蓝、无噪点背景。截图记录。Ctrl+C 停止。

- [ ] **Step 6: 运行测试并提交**

Run: `PYTHONPATH=src pytest`
Expected: PASS（CSS 改动不影响 python 测试）

```bash
git add src/hai_avatar/ui/styles.css
git commit -m "feat: rebuild css token system and app-shell layout"
```

---

### Task 4: 舞台、对话区、气泡、输入、按钮、进度、状态、通知的组件样式

**Files:**
- Modify: `src/hai_avatar/ui/styles.css`（追加组件段）

**Interfaces:**
- Consumes: Task 3 的 token 与布局
- Produces: 全部核心组件的成品样式（spec §4），去 Gradio 味

- [ ] **Step 1: 角色舞台 + 未连接占位 + 暖光**

```css
.hai-avatar-stage {
  position:relative; flex:1; min-height:360px; border-radius:var(--radius-lg);
  overflow:hidden; background:var(--bg-raised); border:1px solid var(--line);
  display:flex; align-items:center; justify-content:center;
}
.hai-avatar-stage iframe { width:100%; height:100%; border:0; position:absolute; inset:0; }
.hai-stage-glow {
  position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(60% 50% at 50% 30%, var(--amber-glow), transparent 70%);
}
.hai-stage-empty { text-align:center; color:var(--text-dim); display:flex; flex-direction:column; gap:var(--space-2); z-index:1; }
.hai-stage-moon { font-size:2.5rem; color:var(--moon); }
.hai-stage-empty span { color:var(--text); }
.hai-stage-empty small { font-size:var(--fs-sm); }
.hai-stage-state { font-size:var(--fs-sm); color:var(--text-dim); }
.hai-stage-caption {
  position:absolute; bottom:var(--space-3); left:0; right:0; text-align:center; z-index:1;
  display:flex; flex-direction:column; gap:2px;
}
.hai-stage-caption span { color:var(--text-strong); }
.hai-stage-caption small { color:var(--text-dim); font-size:var(--fs-xs); }
```

- [ ] **Step 2: 声波（月青，spec §11.3）**

```css
.hai-waveform {
  position:absolute; bottom:44px; left:0; right:0; z-index:1;
  display:flex; align-items:flex-end; justify-content:center; gap:4px; height:28px;
}
.hai-waveform i { width:3px; height:6px; border-radius:2px; background:var(--moon); opacity:.7; }
.hai-waveform.live i { animation:hai-wave 1s ease-in-out infinite; }
.hai-waveform.live i:nth-child(2){ animation-delay:.1s } .hai-waveform.live i:nth-child(3){ animation-delay:.2s }
.hai-waveform.live i:nth-child(4){ animation-delay:.3s } .hai-waveform.live i:nth-child(5){ animation-delay:.2s }
.hai-waveform.live i:nth-child(6){ animation-delay:.1s } .hai-waveform.live i:nth-child(7){ animation-delay:0s }
@keyframes hai-wave { 0%,100%{ height:6px } 50%{ height:22px } }
```

- [ ] **Step 3: 聊天气泡（覆盖 Gradio chatbot）**

```css
#conversation { background:transparent !important; border:0 !important; }
#conversation .message-row, #conversation .message { background:transparent !important; border:0 !important; }
#conversation .message-row .message {
  border-radius:var(--radius-lg) !important; padding:var(--space-3) var(--space-4) !important;
  font-size:var(--fs-lg) !important; line-height:1.5 !important; max-width:78% !important;
  box-shadow:var(--shadow-md);
  animation:hai-bubble .24s cubic-bezier(.2,.8,.2,1) both;
}
/* AI 气泡 */
#conversation .bot .message, #conversation [data-testid="bot"] {
  background:var(--bg-raised) !important; color:var(--text) !important;
  box-shadow:var(--shadow-md), inset 0 1px 0 rgba(255,255,255,.04) !important;
}
/* 用户气泡 */
#conversation .user .message, #conversation [data-testid="user"] {
  background:var(--amber-glow) !important; color:var(--text-strong) !important;
  border:1px solid color-mix(in srgb, var(--amber) 30%, transparent) !important;
}
@keyframes hai-bubble { from{opacity:0; transform:translateY(8px) scale(.98)} to{opacity:1; transform:none} }
```

> 说明：Gradio 版本不同，chatbot 内部类名可能有出入。实现时先在浏览器 DevTools 确认实际类名（`.bot`/`.user` 或 `[data-testid]`），两种选择器都写上作为兜底。

- [ ] **Step 4: 输入框 + 发送按钮 + 快捷 pill**

```css
#message-input textarea {
  background:var(--bg-raised) !important; color:var(--text-strong) !important;
  border:1px solid var(--line) !important; border-radius:var(--radius-md) !important;
  padding:var(--space-3) !important; font-family:var(--font-body) !important; font-size:var(--fs-base) !important;
  transition:border-color .16s ease, box-shadow .16s ease;
}
#message-input textarea::placeholder { color:var(--text-dim) !important; }
#message-input textarea:focus {
  border-color:var(--amber) !important; box-shadow:0 0 0 3px var(--amber-glow) !important;
}
#send-button {
  background:var(--amber) !important; color:var(--bg-base) !important; font-weight:600 !important;
  border:0 !important; border-radius:var(--radius-md) !important; min-height:40px !important;
  transition:background .16s ease, transform .16s ease;
}
#send-button:hover { background:var(--amber-hover) !important; transform:translateY(-1px); }
#send-button:disabled { opacity:.7 !important; transform:none !important; }
#quick-prompts button {
  background:transparent !important; color:var(--text) !important;
  border:1px solid var(--line) !important; border-radius:var(--radius-full) !important;
  transition:background .16s ease, transform .16s ease;
}
#quick-prompts button:hover { background:var(--bg-hover) !important; transform:translateY(-1px); }
```

- [ ] **Step 4b: 兜底覆盖通用 Gradio 按钮味**

```css
.gradio-container button.secondary, .gradio-container .gr-button {
  border-radius:var(--radius-md) !important;
}
```

- [ ] **Step 5: 进度呼吸条**

```css
.hai-progress {
  display:flex; align-items:center; gap:var(--space-3);
  padding:var(--space-3) var(--space-4); background:var(--bg-raised);
  border:1px solid var(--line); border-radius:var(--radius-md);
}
.hai-progress-dot { width:10px; height:10px; border-radius:50%; background:var(--amber); animation:hai-breathe 2s ease-in-out infinite; }
.hai-progress.is-error .hai-progress-dot { background:var(--danger); animation:none; }
.hai-progress-copy { flex:1; display:flex; flex-direction:column; gap:2px; }
.hai-progress-copy b { color:var(--text-strong); font-size:var(--fs-sm); }
.hai-progress-stages { display:flex; gap:var(--space-2); flex-wrap:wrap; }
.hai-progress-stages .done { font-size:var(--fs-xs); color:var(--text-dim); }
.hai-progress-track { width:120px; height:4px; border-radius:var(--radius-full); background:var(--line); overflow:hidden; }
.hai-progress-track i { display:block; height:100%; background:var(--amber); transition:width .3s ease; }
@keyframes hai-breathe { 0%,100%{ transform:scale(1); opacity:1 } 50%{ transform:scale(1.4); opacity:.6 } }
```

- [ ] **Step 6: 状态网格 + 通知 + 诊断 runtime**

```css
.hai-status-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:var(--space-3); }
.hai-status-item {
  background:var(--bg-raised); border:1px solid var(--line); border-radius:var(--radius-md);
  padding:var(--space-3); display:flex; flex-direction:column; gap:2px;
}
.hai-status-item small { color:var(--text-dim); font-size:var(--fs-xs); text-transform:uppercase; letter-spacing:.08em; }
.hai-status-item strong { color:var(--text-strong); font-family:var(--font-mono); font-size:var(--fs-sm); }
.hai-notice {
  padding:var(--space-3) var(--space-4); border-radius:var(--radius-md);
  border:1px solid var(--warn); color:var(--text); background:color-mix(in srgb, var(--warn) 10%, transparent);
  font-size:var(--fs-sm);
}
.hai-notice.error { border-color:var(--danger); background:color-mix(in srgb, var(--danger) 12%, transparent); }
.hai-runtime { display:flex; gap:var(--space-4); font-family:var(--font-mono); font-size:var(--fs-xs); color:var(--text-dim); }
```

- [ ] **Step 7: 目视验证（mock）**

Run: `PYTHONPATH=src python scripts/run_gradio.py`
发送一条消息，确认：气泡浮现动效、输入框 focus 琥珀光、发送按钮暖色、进度呼吸条推进、状态网格卡片化、无 Gradio 默认边框。截图。Ctrl+C。

- [ ] **Step 8: 运行测试并提交**

Run: `PYTHONPATH=src pytest`
Expected: PASS

```bash
git add src/hai_avatar/ui/styles.css
git commit -m "feat: style stage, bubbles, input, buttons, progress, status"
```

---

### Task 5: 富表现力增强 —— 暖光呼吸、进场编排、品牌发光、确认框、响应式、reduced-motion

**Files:**
- Modify: `src/hai_avatar/ui/styles.css`（追加增强段 + Gradio 覆盖节 + 媒体查询）

**Interfaces:**
- Consumes: Task 3/4 的全部样式与类名；`clear-dialog`、`clear-dialog-actions`、`turn-details` elem_id
- Produces: spec §11 视觉增强 + §6 响应式 + §7 reduced-motion 的成品

- [ ] **Step 1: 活的暖光背景（§11.1）**

```css
#experience-shell { position:relative; }
#experience-shell::before {
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:radial-gradient(50% 40% at 50% 12%, var(--amber-glow), transparent 70%);
  animation:hai-ambient 12s ease-in-out infinite;
}
#experience-shell > * { position:relative; z-index:1; }
@keyframes hai-ambient { 0%,100%{ opacity:.6; transform:translateY(0) } 50%{ opacity:1; transform:translateY(-20px) } }
```

- [ ] **Step 2: 品牌发光 hover + 连接点呼吸环（§11.5）**

```css
.hai-brand-mark { transition:box-shadow .2s ease; }
.hai-brand:hover .hai-brand-mark { box-shadow:0 0 28px var(--amber-glow); }
.hai-status-chip.connected .hai-dot { position:relative; }
.hai-status-chip.connected .hai-dot::after {
  content:""; position:absolute; inset:-4px; border-radius:50%;
  border:1px solid var(--moon); animation:hai-ring 2s ease-out infinite;
}
@keyframes hai-ring { 0%{ transform:scale(1); opacity:.6 } 100%{ transform:scale(2); opacity:0 } }
```

- [ ] **Step 3: 首屏进场编排（§11.6）**

```css
#brand-header { animation:hai-in .5s ease both; }
#avatar-panel { animation:hai-in .5s ease .08s both; }
#chat-panel { animation:hai-in .5s ease .16s both; }
@keyframes hai-in { from{ opacity:0; transform:translateY(12px) } to{ opacity:1; transform:none } }
```

- [ ] **Step 4: 清空确认浮层（§4.6）**

```css
#clear-dialog {
  position:fixed !important; inset:0; z-index:50; display:grid !important; place-items:center;
  background:rgba(0,0,0,.5); backdrop-filter:blur(4px);
}
#clear-dialog .hai-dialog-copy, #clear-dialog > * {
  background:var(--bg-raised); border:1px solid var(--line-strong);
  border-radius:var(--radius-xl); box-shadow:var(--shadow-lg); padding:var(--space-6);
  max-width:420px;
}
#clear-dialog h3 { color:var(--text-strong); font-family:var(--font-display); margin:var(--space-2) 0; }
#clear-dialog p { color:var(--text-dim); font-size:var(--fs-sm); }
#clear-confirm { background:var(--danger) !important; color:var(--bg-base) !important; border-radius:var(--radius-md) !important; }
#clear-cancel { background:transparent !important; border:1px solid var(--line) !important; color:var(--text) !important; border-radius:var(--radius-md) !important; }
```

> 说明：Gradio `gr.Group` 渲染结构可能包裹多层，实现时在 DevTools 确认 `#clear-dialog` 直接子级，必要时调整选择器让卡片只作用于内容容器而非整个遮罩层。

- [ ] **Step 5: 响应式（§6）**

```css
@media (max-width:960px) {
  #workspace { grid-template-columns:1fr !important; }
  .hai-avatar-stage { min-height:40vh; }
}
@media (max-width:560px) {
  #experience-shell { padding:var(--space-4); }
  .hai-header { padding:var(--space-3) var(--space-4); }
  .hai-welcome-line { font-size:var(--fs-lg); }
  #quick-prompts { overflow-x:auto; flex-wrap:nowrap !important; }
}
```

- [ ] **Step 6: reduced-motion 兜底（§7）**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation:none !important; transition:none !important; }
  #experience-shell::before { opacity:.6; }
}
```

- [ ] **Step 7: Gradio 覆盖节收尾**

在文件末尾加注释分节，集中放剩余的 Gradio 内部覆盖（accordion 标题、audio 组件、chatbot 容器 padding 等）：

```css
/* ===== Gradio 内部类覆盖（集中管理） ===== */
.gradio-container .label-wrap, .gradio-container .gr-accordion { border-color:var(--line) !important; }
.gradio-container .gr-accordion > button { color:var(--text) !important; }
#reply-audio, #voice-input { background:var(--bg-raised) !important; border-radius:var(--radius-md) !important; }
```

- [ ] **Step 8: 目视验证（mock + prometheus）**

Run（mock）: `PYTHONPATH=src python scripts/run_gradio.py`
确认：暖光缓慢呼吸、进场淡入、品牌 hover 发光、清空确认浮层居中、缩窗到 <960px 变单列。

Run（prometheus）: `AVATAR_PROVIDER=prometheus PYTHONPATH=src python scripts/run_gradio.py`
确认：iframe 舞台正常嵌入、连接点呼吸环、声波在有音频时起伏。

打开系统"减少动态效果"后刷新，确认动画停止。截图各态。Ctrl+C。

- [ ] **Step 9: 运行测试并提交**

Run: `PYTHONPATH=src pytest`
Expected: PASS

```bash
git add src/hai_avatar/ui/styles.css
git commit -m "feat: add ambient glow, reveal, dialog, responsive, reduced-motion"
```

---

### Task 6: 交互舒适度行为（gradio_app.py 行为增强，P0 优先）

**Files:**
- Modify: `src/hai_avatar/ui/gradio_app.py`（create_interface：autofocus、发送后回焦、快捷话题填入并聚焦、发送中 spinner 文案；js 注入）
- Test: `tests/test_gradio_html.py`

**Interfaces:**
- Consumes: Task 2 的 create_interface 结构与 send_outputs 契约
- Produces:
  - 输入框自动聚焦（页面加载 + 发送完成回焦）
  - Enter 发送 / Shift+Enter 换行（沿用现有 `user_input.submit`，无需改）
  - 快捷话题点击 → 填入输入框并聚焦末尾（保留现有 lambda 填入行为，补聚焦）
  - 发送中按钮文案带呼吸点（CSS 已在 Task 4；此处确认按钮 value 文案）

- [ ] **Step 1: 写测试确认 autofocus 注入存在**

在 `tests/test_gradio_html.py` 追加：

```python
def test_message_input_has_elem_id():
    # 确认 create_interface 能构建且 message-input 存在于蓝图
    from hai_avatar.config import load_settings
    settings = load_settings()
    settings = settings.model_copy(deep=True)
    settings.llm.provider = "mock"; settings.tts.provider = "mock"; settings.avatar.provider = "mock"
    app = gradio_app.GradioApp(settings)
    demo = app.create_interface()
    assert demo is not None
```

- [ ] **Step 2: 运行确认通过（构建冒烟）**

Run: `PYTHONPATH=src pytest tests/test_gradio_html.py::test_message_input_has_elem_id -v`
Expected: PASS（若 FAIL 说明 create_interface 重写引入了构建错误，需先修）

- [ ] **Step 3: 加入 autofocus 与回焦 JS**

在 `create_interface` 的 `gr.Blocks(...)` 中，用 `demo.load` 注入聚焦脚本。在 `return demo.queue(...)` 之前添加：

```python
        demo.load(
            fn=None,
            js="""
            () => {
              const focus = () => {
                const el = document.querySelector('#message-input textarea');
                if (el) el.focus();
              };
              setTimeout(focus, 300);
            }
            """,
        )
```

发送完成后回焦：在 `send_btn.click(...)` 之后追加 `.then`：

```python
        send_btn.click(
            fn=respond, inputs=[user_input, chatbot], outputs=send_outputs, api_name="respond",
        ).then(
            fn=None, js="() => { const el=document.querySelector('#message-input textarea'); if(el) el.focus(); }",
        )
```

对 `user_input.submit(...)` 做同样的 `.then` 回焦追加。

- [ ] **Step 4: 快捷话题填入后聚焦**

将三个 prompt 按钮的 click 追加 `.then` 聚焦（保留现有填入 lambda）：

```python
        prompt_one.click(lambda: "最近有点累，想找个人说说。", outputs=user_input).then(
            fn=None, js="() => { const el=document.querySelector('#message-input textarea'); if(el){ el.focus(); el.setSelectionRange(el.value.length, el.value.length);} }",
        )
```

对 prompt_two / prompt_three 同样处理（各自的文案不变）。

- [ ] **Step 5: 运行测试并目视验证**

Run: `PYTHONPATH=src pytest`
Expected: PASS

Run: `PYTHONPATH=src python scripts/run_gradio.py`
确认：加载后光标在输入框；Enter 发送、Shift+Enter 换行；发送完光标回到输入框；点快捷话题后文字填入且聚焦可微调。Ctrl+C。

- [ ] **Step 6: 提交**

```bash
git add src/hai_avatar/ui/gradio_app.py tests/test_gradio_html.py
git commit -m "feat: input autofocus, refocus after send, quick-prompt focus"
```

---

### Task 7: P1 增强 —— 情绪驱动色温（data-emotion）与错误友好降级

**Files:**
- Modify: `src/hai_avatar/ui/gradio_app.py`（respond 完成时写入 data-emotion；TTS 降级用中性提示）、`src/hai_avatar/ui/styles.css`（属性选择器色温）

**Interfaces:**
- Consumes: `PipelineResult.avatar_command.emotion`、`result.warnings`
- Produces:
  - 一个 `gr.HTML(elem_id="emotion-sync")` 输出，respond 完成时写入含 `data-emotion` 的隐藏标记，配合 JS 把属性设到 `#experience-shell`
  - CSS `#experience-shell[data-emotion="happy"]` 等微调 `--amber-glow` 强度/色相（不影响文字色）
  - TTS 失败 warning 用中性 `hai-notice`（非 error 红），文案强调"文字/表情正常"

- [ ] **Step 1: 决策降级路径（低复杂度优先）**

data-emotion 若需新增 output 会改动 send_outputs 长度（违反 Global Constraints）。**改用不扩列的方案**：在 respond 最终 yield 时，通过已有 `warnings_output`（HTML）不承载；改为在 `progress_output` 的 complete HTML 里带一个 `data-emotion` 属性 + 内联 `<script>` 无法执行。**最终决策**：用 `demo.load` 之外的 `.then` JS 读取状态不可行。**采用最简可靠方案**——把 `data-emotion` 写进 `_progress_html` complete 态的根 div（`<div class="hai-progress" data-emotion="happy">`），CSS 用 `.hai-progress[data-emotion=...] ~` 无法反向选中 shell。

因此 **P1 情绪色温降级为：仅让进度呼吸条与呼吸点颜色随情绪变化**（spec §11.2 已允许此降级）。实现：`_progress_html` 增加可选参数 `emotion: str = ""`，complete 态把 emotion 作为 class 加到根：`hai-progress emotion-happy`。

修改 `_progress_html` 签名：

```python
def _progress_html(stage: str = "idle", emotion: str = "") -> str:
```

在 complete 分支根 div 加 class：`class="hai-progress emotion-{html.escape(emotion)}"`（仅当 emotion 非空）。其余调用处 emotion 默认空，兼容不变。

- [ ] **Step 2: 写测试**

```python
def test_progress_complete_carries_emotion_class():
    html = gradio_app._progress_html("complete", emotion="happy")
    assert "emotion-happy" in html


def test_progress_default_no_emotion_class():
    html = gradio_app._progress_html("understanding")
    assert "emotion-" not in html
```

- [ ] **Step 3: 运行确认失败**

Run: `PYTHONPATH=src pytest tests/test_gradio_html.py -k emotion -v`
Expected: FAIL

- [ ] **Step 4: 实现 emotion 参数 + respond 传入**

按 Step 1 修改 `_progress_html`。在 respond 生成器的最终 complete yield 处，把 `_progress_html("complete")` 改为 `_progress_html("complete", emotion=<本轮情绪>)`。本轮情绪来源：`await task` 返回的 status 不含 emotion；需从 result 取。调整 `_process_async` 返回值或在 respond 内解析——**最简**：让 `_process_async` 额外返回 `emotion` 字符串。

修改 `_process_async` 返回签名，末尾追加 emotion：

```python
        return result.reply_text, status, warnings, result.audio_path, result.avatar_command.emotion.value
```

失败分支也补第五个返回值 `"neutral"`。respond 中 `reply, status, warnings, audio = await task` 改为 `reply, status, warnings, audio, emotion = await task`，并在最终 yield 用 `_progress_html(final_stage, emotion=emotion if reply else "")`。

> 注意：`process`（CLI 用）也调用 `_process_async`，其解包为 4 元素——需同步更新为 5 元素或忽略末位。检查 `process` 方法并调整。

- [ ] **Step 5: CSS 情绪色温**

```css
.hai-progress.emotion-happy .hai-progress-dot,
.hai-progress.emotion-supportive .hai-progress-dot { background:var(--amber-hover); box-shadow:0 0 12px var(--amber-glow); }
.hai-progress.emotion-thoughtful .hai-progress-dot,
.hai-progress.emotion-serious .hai-progress-dot { background:var(--moon); }
.hai-progress.emotion-apologetic .hai-progress-dot,
.hai-progress.emotion-confused .hai-progress-dot { background:var(--text-dim); }
```

- [ ] **Step 6: TTS 降级中性化**

当前 warnings 统一进 `_notice`（无 error 则不红）。确认 TTS 失败时 `result.warnings` 走非 error 的 `_notice`（已是默认，`_notice(..., error=False)`）。无需改逻辑，仅确认文案在 pipeline 里为"语音不可用"类中性描述。目视验证即可。

- [ ] **Step 7: 运行测试**

Run: `PYTHONPATH=src pytest`
Expected: PASS（含新 emotion 测试；`process`/`_process_async` 解包一致）

- [ ] **Step 8: 目视验证**

Run: `PYTHONPATH=src python scripts/run_gradio.py`
发送不同情绪触发语（如"我好开心" vs "我最近压力很大"），确认进度点颜色随情绪变化，完成态色温不同。Ctrl+C。

- [ ] **Step 9: 提交**

```bash
git add src/hai_avatar/ui/gradio_app.py src/hai_avatar/ui/styles.css tests/test_gradio_html.py
git commit -m "feat: emotion-reactive progress accent and neutral tts fallback"
```

---

### Task 8: 全量验证与收尾

**Files:**
- 无新增；验证 `src/hai_avatar/ui/gradio_app.py`、`styles.css`

- [ ] **Step 1: 全量测试**

Run: `PYTHONPATH=src pytest`
Expected: 全绿（原有 43 条 + 新增 UI 测试）

- [ ] **Step 2: mock 模式端到端目视**

Run: `PYTHONPATH=src python scripts/run_gradio.py`
逐项核对 spec：暖夜配色、双栏外壳、气泡、输入 focus、进度呼吸条、快捷话题、语音折叠、清空确认、状态网格、通知、暖光呼吸、进场、响应式（拖窗）、reduced-motion。截图归档。

- [ ] **Step 3: prometheus 模式目视**

Run: `AVATAR_PROVIDER=prometheus PYTHONPATH=src python scripts/run_gradio.py`
确认 iframe 舞台、连接 chip、声波、连接点呼吸环。截图。Ctrl+C。

- [ ] **Step 4: 清理与最终提交**

确认无遗留调试代码、无未用函数（`_story_markup` 已删）、无 `.DS_Store` 等误入。

```bash
git add -A src/hai_avatar/ui/
git commit -m "chore: finalize frontend redesign" --allow-empty
```

- [ ] **Step 5: 汇报**

汇总：改动文件、测试结果、mock/prometheus 目视结论、spec 覆盖情况。

---

## Self-Review

**1. Spec coverage：**
- §2 配色/字体/间距/圆角/阴影 → Task 3 Step 1
- §3 布局架构（header/双栏/删 story/填满视口）→ Task 2（HTML）+ Task 3 Step 3-4
- §4 组件（按钮/输入/chip/进度/气泡/对话框）→ Task 4 + Task 5 Step 4
- §5 动效（过渡/浮现/呼吸/reduced-motion）→ Task 4/5 + Task 5 Step 6
- §6 响应式 → Task 5 Step 5
- §7 可访问性（对比/focus/aria/reduced-motion）→ Task 3 Step 2 + Task 5 Step 6（aria 由 HTML 函数保留）
- §8 契约（elem_id/函数签名/send_outputs/删 story）→ Task 1/2 契约 + Global Constraints
- §11 富表现力（暖光/情绪色温/声波/立体气泡/品牌发光/进场）→ Task 4 Step 2-3 + Task 5 Step 1-3 + Task 7
- §12 交互（autofocus/Enter/快捷话题/进度/错误友好/清空/Esc）→ Task 6 + Task 7 Step 6（Esc 关闭标注为可选，见下）

**发现的 gap 与处理：**
- §12.7 Esc/点击遮罩关闭清空框：Gradio 事件难以可靠绑定 Esc，已在 spec 标为可选增强（§12.8 P1）；计划未强制实现，Task 5 Step 4 仅做遮罩+居中样式。**可接受**（P1，spec 允许降级）。
- §12.2 快捷话题"直接发送 vs 填入"：spec 已决策为"填入并聚焦"，Task 6 Step 4 实现填入+聚焦。一致。
- §11.2 情绪色温：原设计想影响全局暖光，Task 7 Step 1 决策降级为仅进度点色温（spec §11.2 明确允许此降级）。一致。

**2. Placeholder scan：** 无 TBD/TODO；所有 code step 含完整代码；未出现"类似 Task N"式省略。Task 4 Step 3 与 Task 5 Step 4 对 Gradio 内部类的不确定性已用"DevTools 确认 + 双选择器兜底"明确处理，非占位。

**3. Type consistency：**
- `_progress_html` 签名演进：Task 2 为 `(stage)`；Task 7 扩为 `(stage, emotion="")`，默认值保证 Task 2/6 调用兼容。一致。
- `_process_async` 返回：原 4 元组 →Task 7 扩为 5 元组（+emotion），同步更新 `process` 与 respond 解包。Task 7 Step 4 已显式要求更新两处调用点。一致。
- `send_outputs` 8 项顺序：Global Constraints + Task 2 契约锁定，后续任务不改列长。一致。
