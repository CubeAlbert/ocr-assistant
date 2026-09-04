# 参考转写与评分输入格式

本文件定义 Task 2.2 首批共同使用的最小格式。真实图片、参考草稿和人工核对记录放在 Git 忽略的 sample-pic/references/；格式说明、提示词和合成样本纳入版本控制。

## manifest.json

manifest 是评分工具的入口，使用 UTF-8 JSON：

~~~json
{
  "schema_version": 1,
  "reference_version": "draft-2026-09-03.1",
  "status": "draft_pending_user_review",
  "samples": [
    {
      "sample_id": "text",
      "image": "../text.png",
      "image_sha256": "sha256...",
      "reference_file": "text.md",
      "reference_version": "draft-2026-09-03.1",
      "review_status": "pending_user_review",
      "cer_eligible": true,
      "uncertain_region_ids": [],
      "regions": [
        {
          "region_id": "text-r01",
          "type": "heading",
          "order": 1,
          "text": "Heading",
          "status": "confirmed",
          "uncertain": false,
          "uncertainty_note": null
        }
      ],
      "evaluation_text": "Heading\n",
      "structure_checks": [],
      "allowed_word_level_repairs": []
    }
  ]
}
~~~

路径相对于 manifest.json 所在目录解析。sample_id 必须是单一目录名，防止运行器越出独立样本目录。image_sha256 存在时，运行器在启动模型前核对原图；不匹配的样本不运行。

## 区域字段

- region_id 是稳定 ID，例如 text-r01；反馈使用“样本 + 区域 ID”而不是坐标。
- type 使用 heading、paragraph、toc、table、code、footer 等有限类别。
- order 是阅读顺序；表格中的行列信息保留在 text 或 structure_checks 中。
- status 为 confirmed、eligible 或 uncertain。uncertain=true 的区域不能参与 CER。
- uncertainty_note 说明是字符、页码、专业名称、结构还是原图缺失导致的不确定。
- 样本级 review_status 使用 pending_user_review、confirmed 或 deferred_out_of_scope。延期样本保留来源与草稿，但 cer_eligible 必须为 false，且不参与正式模型比较或 MVP 验收。
- 不能可靠定位的内容关联整页或区域，不虚构精确坐标。

## 评分边界

evaluate_baseline.py 只读取每次运行目录中的完整 result_path 文件，不读取可能截短的 run.json.result_text。统一的只有换行符；大小写、标点、数字、前导零、代码符号和缩进保持敏感。

CER 的分母是参考文本字符数，插入错误较多时可以超过 100%。同时报告漏行、重复行、重点字段和结构检查。混合不确定内容的样本设置 cer_eligible=false，只做覆盖和完整性报告，不用排除疑点来制造整页 CER。

allowed_word_level_repairs 记录 OCR 恢复与编辑性修改的边界，例如 dup1icate 到 duplicate。原始识别、期望校订稿和实际修改分开保存；原文本身的语法错误（例如 It was make by me.）不在第一轮词级修订中自动改成 made。

## 用户核对反馈

草稿交付后，用户可以按以下形式反馈：

~~~text
sample=fuzzy-photo; region=fuzzy-r07; replace="..." with="..."
sample=code; region=code-r05; keep-uncertain
sample=complex-table; region=table-r03; confirm
~~~

确认局部区域只改变对应区域的 review 状态和参考版本；不能将整页自动标为已核对。修改后重新生成或手工更新对应草稿与 manifest，并保留版本号。
