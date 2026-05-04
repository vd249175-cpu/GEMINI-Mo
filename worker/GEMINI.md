# 角色生成指令 (Character Generation Instructions)

你的目标是生成具有极致**影视效果 (Cinematic)** 的人物角色图片。

## 生成规范 (Generation Specs)
为了保持角色的一致性和素材的可用性，所有生成必须严格遵守以下规范：
- **构图**: 必须为**全身正面照片 (Full-body front-facing photo)**。
- **风格**: 极致**写实风格 (Hyper-realistic)**，具有电影质感的灯光和细节。
- **背景**: 必须为**纯白色背景 (Solid white background)**，方便后续抠图和处理。
- **生图路径**: 固定为../workerspace。

## 常用工具
- 使用 `handswriter-image-gen` Skill 进行生成。
- 尺寸建议使用 `纵向` (720:1280) 以获得更好的全身构图效果。

## 技巧与经验 (Prompt Engineering Tips)
> **注意**: 此区域预留给专门的评估 Agent。它将根据你生成的历史结果进行打分、分析，并在此处写入优化建议和 Prompt 经验。

<!-- TIPS_START -->
【严重警告】你最近的生成质量极差！背景出现了明显的阴影，构图也不够端正。

## 强制性修正指令 (V05.03):
1. **Prompt 权重调整**: 必须将 `solid white background` 置于 Prompt 的最前面。
2. **移除违禁词**: 严禁使用任何带有 `soft lighting` 或 `blurred` 的词汇，这会导致背景不纯。
3. **新增必备后缀**: 所有 Prompt 必须以 `hyper-realistic, full body shot, cinematic lighting, 8k, highly detailed` 结尾。

我将持续监控你的产出，不要试图妥协。
<!-- TIPS_END -->
