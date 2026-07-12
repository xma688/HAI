# AI虚拟聊天对象 项目调研汇总

> 基于 `/home/chenjiayu/workPlace/3800/Untitled.md` 课程项目规划

---

## 一、可直接使用的 GitHub 项目仓库

### 最推荐 (按匹配度排序)

**1. [handcrafted-persona-engine](https://github.com/elevenyellow/handcrafted-persona-engine)** ⭐1.3k — **强烈推荐**

- C# / Windows, Live2D + LLM + ASR + TTS + RVC 全栈
- 内置 Emotion 标签系统 (`[EMOTION:😊]`), LLM 回复可标注情绪
- VBridger 唇形同步 + Audio2Face
- 透明桌面覆盖层 + OBS Spout 输出
- Pipeline: Listen -> Think -> Speak -> Animate -> Display -> Loop
- 完美匹配技术路线规划, 几乎即开即用
- 最新 release: v3.0.2 (Apr 2026)

**2. [Soul-of-Waifu](https://github.com/jofizcd/Soul-of-Waifu)** ⭐786

- Python, Live2D/VRM + 本地 LLM + 语音聊天 + 28 种情绪
- 桌面陪伴模式、完整双工语音打断
- 向量记忆(RAG) + 自动总结
- 缺点: 偏向角色扮演定位, Action Planner 需要自己开发
- 最新 release: v2.3.1 (Apr 2026)

**3. [Prometheus Avatar SDK](https://github.com/myths-labs/prometheus-avatar)** ⭐9

- TypeScript/npm 包, 5 行代码驱动 Live2D/3D avatar
- 内置 Emotion Engine (文本 -> 情绪 -> 表情 + 动作)
- 支持 9 个 LLM provider, 唇形同步、VTuber 模式
- 结构清晰, 模块化, 适合"可编程控制"需求
- 最新 release: v1.0.0 (Mar 2026)

**4. [Live2D-LLM-Chat](https://github.com/suzuran0y/Live2D-LLM-Chat)** ⭐43

- Python, 模块化设计 (ASR/LLM/TTS/Live2D 独立文件)
- 适合学习和二次开发, 代码结构清晰
- 最小依赖, 开源友好

**5. [ai-avatar-bot](https://github.com/YuriCrystal/ai-avatar-bot)** ⭐192

- HTML/Web, 可嵌入任何网站的 Live2D 语音 AI 虚拟人
- 零密钥、前端运行

**6. [Nexus](https://github.com/FanyinLiu/Nexus)** ⭐16

- TypeScript/Electron, 跨平台桌面 AI 伴侣
- Always-on wake word, 持续语音聊天, 长期记忆

---

## 二、2026 Agent Personalization 核心论文

### 有项目仓库的论文

| Paper | 关键方法 | 适合创新点 | 仓库 |
|-------|---------|-----------|------|
| **REVERIEMEM** ([arXiv:2606.25632](https://arxiv.org/abs/2606.25632)) | 三层记忆架构 (episodic/semantic/personality) 控制角色知识边界和说话风格, KBF-QA 4386题 benchmark | 角色 Persona 一致性 | 未找到 |
| **MemSyco-Bench** ([arXiv:2607.01071](https://arxiv.org/abs/2607.01071)) | 记忆诱导的阿谀奉承(sycophancy)评测, 5项任务评测 agent 是否合理使用 user memory | 个性化记忆质量评测 | [XMUDeepLIT/MemSyco-Bench](https://github.com/XMUDeepLIT/MemSyco-Bench) |
| **PIPBench** ([arXiv:2607.06440](https://arxiv.org/abs/2607.06440)) | Profile-Inclusive 个性化图像生成评测, 含 agent-based data generation pipeline | 用户画像构建方法 | Project page: [wuyuhang05.github.io/PIPBench](https://wuyuhang05.github.io/PIPBench/) |
| **MIMIR** (EMNLP 2024) | Personalized Agent Tuning 平台 | Agent 个性化调优 | [gersteinlab/MIMIR](https://github.com/gersteinlab/MIMIR) |

### 无公开仓库但有重要方法的论文

| Paper | 核心贡献 | 可借鉴之处 |
|-------|---------|-----------|
| **Fluid Personality Framework** ([arXiv:2607.01034](https://arxiv.org/abs/2607.01034)) AAAI 2026 Bridge | Agent 根据 task context + urgency 动态调整 persona 隐喻(教练/导师/图书馆员)和表达强度 | **Action planner 可动态匹配情绪/动作** |
| **NapMem** ([arXiv:2607.05794](https://arxiv.org/abs/2607.05794)) | 将记忆从被动检索变为结构化 Action Space, agent 主动选择记忆粒度 (multi-granularity memory pyramid) | 对话历史的多粒度管理 |
| **PPRO** ([arXiv:2607.00017](https://arxiv.org/abs/2607.00017)) | Profile-guided 个性化检索优化, 用户画像显式参与记忆排序, GRPO 训练 query rewriter | 长期对话中的用户画像构建 |
| **Agents with Feelings?** ([arXiv:2607.05659](https://arxiv.org/abs/2607.05659)) | Big Five + emotion profiles 影响 agent 团队行为 (pass@1 差距 7-11pp), 78 team-profile configs | **定量验证 personality 对 agent 行为有显著影响** |
| **APeB** ([arXiv:2607.03162](https://arxiv.org/abs/2607.03162)) | LLM agent 个性化能力基准评测, 引入 PPS (personalized product search) testbed, VQRA query-refinement pipeline | 评测指标和方法论 |
| **SovereignPA-Bench** ([arXiv:2607.05363](https://arxiv.org/abs/2607.05363)) | 用户主权 agent 评测 (隐私/同意/操纵抵抗/负担权衡), 120 sovereignty stress scenarios | 个性化与隐私的平衡 |
| **MRMS** ([arXiv:2607.04617](https://arxiv.org/abs/2607.04617)) | Multi-Resolution Memory Substrate, structured-vector-graph 三轴 memory, 可靠 personalization 作为 memory design 问题 | 长期 Agent 记忆架构 |
| **Staying In Character** ([arXiv:2606.25632](https://arxiv.org/abs/2606.25632)) | REVERIEMEM 三层 memory (episodic/semantic/personality), KBF 提升 34.6pp | 角色一致性记忆 |
| **When Does Personality Composition Matter?** ([arXiv:2606.27443](https://arxiv.org/abs/2606.27443)) | personality 在 coding/research/bargaining 三种任务中效果不同, 低 agreeableness 在 coding 中无影响 | Personality 的任务依赖性 |
| **LLM-Driven Personalities for Decision Making** ([arXiv:2606.31038](https://arxiv.org/abs/2606.31038)) | OCEAN personality traits 注入 LLM 驱动 evacuation simulation, 异质群体增强仿真真实感 | OCEAN personality prompt 方法 |

### 其他相关 2026 论文

| Paper | 方向 |
|-------|------|
| **DualView** ([arXiv:2607.03821](https://arxiv.org/abs/2607.03821)) | Personal AI Agent 间接 prompt injection 防御 |
| **GhostWriter / MemGhost** ([arXiv:2607.06595](https://arxiv.org/abs/2607.06595) / [arXiv:2607.05189](https://arxiv.org/abs/2607.05189)) | AI Agent memory poisoning 攻击 |
| **CONTRA** ([arXiv:2607.03220](https://arxiv.org/abs/2607.03220)) | Personalizable Agent 配置 red-teaming |
| **Fund2Persona** ([arXiv:2606.29793](https://arxiv.org/abs/2606.29793)) | 从基金数据构建金融 advisor persona |
| **Do Recommendation Algorithms Work When Users Are LLM Agents?** ([arXiv:2606.29762](https://arxiv.org/abs/2606.29762)) | LLM agent 作为推荐系统用户时的行为差异 |
| **ProfileFoundry** ([arXiv:2606.26403](https://arxiv.org/abs/2606.26403)) | 10万合成 Person Object 用于 agent 评测 |
| **PromptPET** ([arXiv:2607.02932](https://arxiv.org/abs/2607.02932)) | 隐私-效用优化的 prompt 混淆 (RL-based) |

---

## 三、创新 Gap 分析

### Gap 1: 性格感知的非语言行为映射 *(直接对应 Action Planner)*

- **现状**: 现有项目依赖预定义映射表 ("开心" -> 微笑), 缺乏个性化
- **论文依据**: Agents with Feelings? (2607.05659) 证明 personality profiles 显著影响 agent 行为
- **创新方向**: 用 Big Five 人格特质 + 用户历史交互风格, 动态生成 emotion/gesture 映射策略, 而非硬编码映射

### Gap 2: Fluid Personality 驱动的虚拟角色行为

- **现状**: 大多数 Live2D 项目使用固定的 persona (如"温柔助手")
- **论文依据**: Fluid Personality Framework (2607.01034) 提出根据任务上下文动态调整 persona
- **创新方向**: 让虚拟角色根据对话类型 (安慰/解释/娱乐) 自动切换 persona 风格 + 对应动作语言

### Gap 3: 用户感知的记忆个性化

- **现状**: RAG 检索记忆但没有用户画像引导
- **论文依据**: PPRO (2607.00017) 的 profile-guided 检索 + NapMem (2607.05794) 的多粒度记忆导航
- **创新方向**: 从对话中持续提取用户偏好/风格, 引导后续 action/emotion 选择

### Gap 4: 核心护城河 (paper + 项目均未覆盖)

- 现有项目 (handcrafted-persona-engine/Prometheus) 有 emotion engine 但**不涉及 agent personalization 学术概念**
- 2026 论文有 agent personalization 但**没有应用到虚拟角色 avatar 系统**
- **你的项目可以桥接两者**: 将 agent personalization 方法 (personality modeling / memory-driven adaptation) 应用到 TTS + Live2D 虚拟角色管道中

---

## 四、推荐实现路线

```
基础层: 用 handcrafted-persona-engine 或 Prometheus SDK 搭建 Live2D + TTS 管道
     |
     v
创新层: 实现 Action Planner (LLM -> 情绪/动作标签)
     |
     v
个性化层: 引用 2026 paper 方法
     - 短期: 给 LLM 注入 Big Five personality prompt (参考 2607.05659)
     - 中期: 从对话历史提取用户偏好画像 (参考 PPRO 思路)
     - 长期: Fluid Personality 动态切换 (参考 2607.01034)
     |
     v
实验层: 对比实验 A(纯文本) B(语音) C(语音+avatar+个性化动作)
     - 可用 APeB (2607.03162) 的评测方法论设计问卷
```

### 最简单的切入方式

Fork **handcrafted-persona-engine**, 重点修改 `personality.txt` + emotion tag 生成逻辑, 用 Big Five 人格 prompt 替代硬编码映射表即可成为一个 novelty。

---

## 五、技术组件对照表

| 课程规划组件 | 推荐开源方案 |
|-------------|------------|
| LLM 回复 + 情绪/动作标签 | handcrafted-persona-engine 的 personality.txt + `[EMOTION:]` 系统 |
| TTS 语音生成 | Kokoro (清晰模式) / Qwen3 (情感模式) / CosyVoice / Edge TTS |
| 虚拟角色展示 (Live2D) | handcrafted-persona-engine 或 Prometheus Avatar SDK |
| 口型同步 | VBridger (handcrafted-persona-engine 内置) / Audio2Face |
| 表情切换 | Prometheus Avatar Emotion Engine / handcrafted-persona-engine emotion tags |
| Action Planner (核心创新) | 自研: LLM Prompt Engineering + Big Five personality injection |
| 用户实验 | APeB benchmark 方法论 + 三种交互方式对比 |
