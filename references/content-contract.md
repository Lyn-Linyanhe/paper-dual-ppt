# 内容与计划契约 v1

`paper_tools init`创建空白`content.json`和两版计划。空白不是完成内容，不得通过填充占位句来满足检查。

## content.json

- `schema_version`: 1。
- `paper`: `title`, `type`, `source_id`，type来自paper-types指南。
- `sources`: 每项`id`, `path`（项目内相对路径）, `sha256`, `pages`。补充来源独立编号，不覆盖原文。
- `units`: 原文单元。每项`id`, `kind`（abstract/introduction/other）, `quote`, `explanation`, `argument_role`, `source_id`, `page`（物理页，从1起）, `printed_page`, `section`。可加`rects`与阅读顺序；精确引文先回原页核验。PDF双栏、断词和连字必须回原页确认，不能把转换文本顺序当作证据。
- `claims`: 每项`id`, `text`, `kind`（author_claim/result/author_interpretation/teaching/our_suggestion）, `source_id`, `page`, `section`, `quote`（证据摘录）, `boundary`（明确支持范围）；自行教学例子也给关联原文而非假称直接引文。统计结构可加`statistic`, `sample`, `metric_direction`, `uncertainty`, `comparison`，未知填null及原因。
- `methods`: 每项`id`, `purpose`, `input`（参与者/数据）, `procedure`, `measure`, `analysis`, `output`, `source_id`, `page`；未报告值写“未报告”，不适用写理由。
- `figures`: 每项`id`（如fig-1/table-1）, `label`, `scope`（body/supplement）, `source_id`, `page`, `caption`, `path`, `question`, `reading`, `claim_ids`, `boundary`。复合图可增加subpanels。截图应真实存在。
- `resources`: 每项`id`, `type`（system_demo/generated_sample/stimulus/third_party）, `url`, `identity_evidence`, `accessed`, `status`, `usage`, `playback`。没有找到用独立调查记录表达，不伪造资源条目。官方入口、介绍视频、生成样片、实验刺激和第三方报道必须分别标注；网页列出不等于已播放，未确认的实验刺激或补充材料写入调查记录而不是伪造资源条目。
- `coverage`: `abstract_complete`, `introduction_complete`, `body_inventory_complete`（布尔值，人工核验后设true），`supplement_status`, `limitations`（数组）。这些声明不是机器证明全文完整。正文编号图表清单必须以人工核验为准；扫描件、缺页或缺补充材料要写明降级范围。

## plans/brief.json / detailed.json

`variant`为brief/detailed；`slides`按实际页序排列。每项：

```json
{"id":"P01","title":"研究为什么需要这项方法？","job":"解释研究动机","role":"motivation","claim_ids":["c01"],"unit_ids":["intro-01"],"figure_ids":[],"method_ids":[],"appendix":false,"note":"04_备课备注/detailed/P01.md","seconds":60}
```

ID每版内唯一；页序由数组决定。标题重复时，每页必须有全版唯一的`page_marker`，且最终PPTX与PDF对应页都要能提取该标记。每页必须有一个与计划标题一致的原生title/ctrTitle占位符，用于真实页序验证。两版引用同一content；关键结果不另抄一份。详细版引用全部摘要/Introduction单元和正文图表，可分布主线/附录。brief可省精读细节但不能改结论。所有备注真实存在且实质完整。

## 交付检查输入

`config.json`中`media_allowlist`和`external_allowlist`默认为空数组。每项许可必须有`variant`（brief/detailed）、`target`、`reviewer`、`status: pass`、项目相对`evidence`和`evidence_sha256`。实际出现的同版同目标必须恰好匹配一项；媒体还必须有与PPTX内成员字节一致的`target_sha256`。许可证据变化和媒体替换均需重新核验。外链许可仅绑定URL与证据快照，不保证远端内容以后不变；实际播放另记证据。旧的布尔allow_media/allow_external_relationships不能放行。

`sensitive_terms`是非空字符串数组，扫描PPTX全部XML/关系及PDF提取文本，不做OCR。路径扫描识别Windows盘符、UNC、file URI及常见POSIX根目录；不是任意文字内容的隐私证明。嵌入对象、批注、本机路径始终阻断。

`delivery.json`：

```json
{"variants":[{"variant":"brief","pptx":"02_精简汇报版/论文_精简汇报版.pptx","pdf":"02_精简汇报版/论文_精简汇报版.pdf"},{"variant":"detailed","pptx":"03_详细精读版/论文_详细精读版.pptx","pdf":"03_详细精读版/论文_详细精读版.pdf"}]}
```

`07_验收/reviews.json`含`content`与`visual`两个对象，每个`status`为pending/pass/fail，`reviewer`、`scope`、`evidence`、`issues`、`artifacts`（项目相对文件路径→sha256）。证据为实际检查记录/图；核验时记录PPTX/PDF以及内容、计划、备注、配置和被引用来源文件的版本哈希。不得写预设pass。改变任一绑定输入或成品哈希会使记录过期。内容核验应含正文与备注，视觉核验含所有实际渲染页面；机器仅检查绑定和记录完整性。`check-delivery`会返回`input_hashes`与`artifact_hashes`，而不会把它们自动写成通过记录。
