---
deck_id: neutral-academic
kind: deck
category: scenario
summary: 论文课堂讲解与原文精读，支持研究方法、证据和结论边界说明
keywords: [paper, evidence, teaching, reading]
primary_color: "#285A9F"
canvas_format: ppt169
canvas_width: 1280
canvas_height: 720
canvas_viewbox: "0 0 1280 720"
replication_mode: standard
native_structure_mode: structured
page_count: 7
placeholders:
  01_cover: ["{{TITLE}}", "{{SUBTITLE}}", "{{AUTHOR}}"]
  02_chapter: ["{{CHAPTER_NUM}}", "{{CHAPTER_TITLE}}", "{{CHAPTER_DESC}}"]
  03a_content_quote: ["{{PAGE_TITLE}}", "{{ORIGINAL}}", "{{EXPLANATION}}", "{{SOURCE}}", "{{PAGE_NUM}}"]
  03b_content_flow: ["{{PAGE_TITLE}}", "{{PROCEDURE}}", "{{MEASUREMENT}}", "{{SOURCE}}", "{{PAGE_NUM}}"]
  03c_content_compare: ["{{PAGE_TITLE}}", "{{COLUMN_1}}", "{{COLUMN_2}}", "{{COLUMN_3}}", "{{SOURCE}}", "{{PAGE_NUM}}"]
  03d_content_evidence: ["{{PAGE_TITLE}}", "{{FIGURE_AREA}}", "{{READING}}", "{{SOURCE}}", "{{PAGE_NUM}}"]
  04_ending: ["{{THANK_YOU}}", "{{CLOSING_MESSAGE}}", "{{PAGE_NUM}}"]
---

# Neutral Academic — Design Specification

## I. Template Overview

论文课堂讲解、自学备课和证据精读。受众为初读论文的师生；原文对照与方法流程是代表性场景，不规定下游页序和页数。白底蓝色强调，无学校/作者身份资产。画布16:9，1280×720。

## II. Color Scheme

| Role | HEX |
|---|---|
| Primary | #285A9F |
| Text | #172B46 |
| Secondary | #53657A |
| Rule | #D8E2EE |
| Background | #FFFFFF |

## III. Typography

Latin Arial；EA Microsoft YaHei；均不嵌入/附送字体文件。目标为安装相应字体的Windows PowerPoint，其他机器需复核替代字体并使用PDF备份。标题38–48px、正文28–30px、来源16px为模板样例；实际项目按阅读距离调整。

## IV. Signature Design Elements

单一academic-master，左上短蓝线与底部分隔线作为跨页定位。正文左右不等宽与并列三栏分别服务原文/读法和方案对照，不引入固定统计或学科符号。矩形画布留白优于书页折角等暗示文档身份的装饰；分组通过轴线与留白表达，避免伪流程箭头。每个Layout槽位起点左上；来源与页码分开。无图片、图标、嵌入文件和外链。

## V. Page Roster

| Prototype | Layout key / picker | Slots and capacity / character |
|---|---|
| `01_cover.svg` | cover / 论文封面与路线 | 上部双行标题，中部论文定位，下部作者/路线；48/28/22px，标题区160高；slots: TITLE, SUBTITLE, AUTHOR；Arial/微软雅黑，左上换行 |
| `02_chapter.svg` | chapter / 章节与论证任务 | 左侧章节编号，右侧标题/任务；非时间线，不暗示因果；slots: CHAPTER_NUM, CHAPTER_TITLE, CHAPTER_DESC；Arial/微软雅黑，左上换行 |
| `03a_content_quote.svg` | quote / 原文与解释 | 左英文摘录/截图区域，右概括与边界；各列400高，原图可作为Slide-local替代内容而非强塞文本槽；slots: PAGE_TITLE, ORIGINAL, EXPLANATION, SOURCE, PAGE_NUM；Arial/微软雅黑，左上换行 |
| `03b_content_flow.svg` | flow / 证据获取流程 | 上部流程，下部测量与证据；不预设参与者/实验类型；slots: PAGE_TITLE, PROCEDURE, MEASUREMENT, SOURCE, PAGE_NUM；Arial/微软雅黑，左上换行 |
| `03c_content_compare.svg` | compare / 方案或结论边界对照 | 三个对照对象，等宽只表达并列，不预设优劣；28px；slots: PAGE_TITLE, COLUMN_1, COLUMN_2, COLUMN_3, SOURCE, PAGE_NUM；Arial/微软雅黑，左上换行 |
| `03d_content_evidence.svg` | evidence / 图表与结论 | 左大图/表区域，右读法与结论边界；原图使用图片时按实际布局声明picture或允许的Slide-local内容，不以占位文本冒充图片；slots: PAGE_TITLE, FIGURE_AREA, READING, SOURCE, PAGE_NUM；Arial/微软雅黑，左上换行 |
| `04_ending.svg` | ending / 结论与讨论 | 上部总结标题，下部核心结论/讨论；不含联系信息或个人身份；slots: THANK_YOU, CLOSING_MESSAGE, PAGE_NUM；Arial/微软雅黑，左上换行 |
