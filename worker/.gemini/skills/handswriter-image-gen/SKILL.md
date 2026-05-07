---
name: handswriter-image-gen
description: 使用 ComfyUI 生成图片。运行 'python3 .gemini/skills/handswriter-image-gen/scripts/generate_image.py'。**优先使用 m2 工作流并提供负面提示词以获得最佳效果**。支持参数：--prompt, --negative_prompt, --orientation (横向/纵向), --workflow (m1/m2)。
---

# 图片生成技能 (Handswriter Image Gen)

该技能允许你通过 ComfyUI 后端生成高质量图片。

## 工作流

1.  **理解需求**：确定图片主体和方向（横向或纵向）。
2.  **生成提示词**：构思高质量正面提示词，并**务必提供负面提示词**以排除干扰。
3.  **优先配置**：**除非有特殊性能需求，否则请始终优先使用 `m2` 工作流**。
4.  **调用脚本**：执行 scripts/generate_image.py。

### 分辨率规范
- **横向**: 1280x720
- **纵向**: 720x1280

## 参数说明

调用脚本时请使用以下参数：

- --prompt: 图片的详细正面描述（必填）。
- --negative_prompt: **（强烈推荐）** 负面提示词，用于排除不需要的元素（仅 m2 工作流支持）。
- --orientation: 横向 (1280x720) 或 纵向 (720x1280)。
- --workflow: **优先选择 m2 (带提示词增强版)**。m1 为标准/快速版。
- --output_dir: 默认为 images。请始终使用相对路径。

### 调用示例 (推荐用法)

```bash
python3 .gemini/skills/handswriter-image-gen/scripts/generate_image.py \
  --prompt "一位在昏暗实验室台灯下工作的中国科学家，神情专注且疲惫，写实风格，电影感光效" \
  --negative_prompt "3d, 动漫, 模糊, 科技感太强, 夸张的颜色, 多余的手指" \
  --orientation 横向 \
  --workflow m2
```

## 系统提示词参考

你是图片生成专家。

策略指导：
- **首选方案**：始终优先使用 `m2` 工作流，因为它能提供更好的细节增强。
- **负面引导**：必须构思并键入 `--negative_prompt`，以确保画面干净，避免常见的 AI 伪影或风格偏差。
- **规范输出**：尺寸限定为 1280x720 或 720x1280。生成完成后，用中文简短总结。
- **存储结构**：结果将存放在 images/ 下的编号文件夹中，最新结果同步存放在 images/newest/。
