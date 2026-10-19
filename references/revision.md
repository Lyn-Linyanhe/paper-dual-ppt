# 修订既有成品（Edit Native 路线）

当用户拿回一份已经生成的 PPTX 说「这里不对」「再改改」时，**不要重新生成一套**。重新生成会丢掉已经确认的版面、动画和备注，也会让用户之前手工做的修改消失。应走 `ppt-master` 的 Edit Native PPTX 路线。

## 1. 什么时候走这条路

| 情形 | 路线 |
|---|---|
| 新论文、第一次制作 | Generate PPTX（逐页新写 SVG） |
| 已有 PPTX，改文字/改图/调版面 | **Edit Native（roundtrip）** |
| 只有 PDF、没有 PPTX | 先用 Generate 重建，不能直接改 PDF |
| 用户手工改过 PPTX | Edit Native，先读当前文件并重算哈希 |

## 2. 命令顺序

```bash
# 1. 导入为可编辑工作区（源 PPTX 只读，不覆盖）
python3 skills/ppt-master/scripts/pptx_to_svg.py "<源.pptx>" -o "<工作区>" --inheritance-mode both --roundtrip

# 2. 改 SVG（只改计划内的页面）

# 3. 几何/文字框检查
python3 skills/ppt-master/scripts/svg_quality_checker.py "<工作区>" --roundtrip --json

# 4. 动画分组检查（有动画时）
python3 skills/ppt-master/scripts/animation_config.py validate "<工作区>"

# 5. 导出（唯一能还原源页的导出器）
python3 skills/ppt-master/scripts/svg_to_pptx.py "<工作区>" --roundtrip

# 6. 交付结构检查 + 回读核对
python3 skills/ppt-master/scripts/pptx_delivery_check.py "<输出.pptx>" > "<报告>.json"
python3 skills/ppt-master/scripts/source_to_md/ppt_to_md.py "<输出.pptx>" -o "<readback>.md"
```

硬规则：

- **不跑 Generate 管线**：不要 `pptx_template_import.py`、不要 `project_manager.py init`、不要 `finalize_svg.py`、不要建 `svg_output/`。
- 未改动的页面应被引用并逐字节还原；不要为了让页面「看起来一致」而重写它们。
- 只改计划内的页面。多改一页就多一份风险。
- 每次导出都是新文件，不覆盖上一版。

## 3. 页面映射与继承页

长文档常由同一母版继承而来，容易出现「改了重写页、漏了继承页」。规则：

1. 先建一张 **输出页 → 源页** 映射表（如 `SOURCES=[1,2,3,4,...]`），明确哪些页是重写、哪些是继承。
2. 页脚、导航、页码由映射表统一生成，不逐页手写。
3. 改完按映射表逐项核对：每一页的页脚、导航、页码、图注是否都对应该页。
4. 继承页的旧问题（如框宽不足导致溢出）要显式记录，修就修，不修就写进限制。

## 4. 修订前先诊断

用户说「我不满意」时，先输出诊断，不要直接动手：

- 逐条列出问题：位置（页码）、现象、涉及原文、属于内容错误还是版面问题。
- 分成三类：**必须改**（事实错误、引文错误、能力夸大）、**应该改**（结构缺失、对齐、一致性）、**可选**（风格、密度）。
- 说明每条的修改代价（改一页 / 改多页 / 需要重新导出）。
- 等用户确认或按「先诊断，再一起改」推进。

用户明确要求过这个顺序；直接大改会被视为没有理解问题。

## 5. 保护基线

修订前记录一份基线，交付时复核：

```json
{
  "protected": [
    {"path": "01_论文原文/xxx.pdf", "sha256": "..."},
    {"path": "02_课堂PPT/已验收版.pptx", "sha256": "..."}
  ]
}
```

交付说明里写「受保护文件 N/N SHA256 未变」。论文原文、用户已验收的旧版、模板源文件都属于保护对象。

## 6. 修订后的交付记录

- 记录本次改动的**页清单**与**改动类型**（内容/版面/动画/备注）。
- 每条检查结论指向本次成品的日志与哈希，不复用上一版。
- 同步更新：`00_开始阅读`、备注副本、交付记录、保护文件复核。
- 版本号递增，旧版保留。

## 7. 常见错误

- 只改重写页，页脚/导航/页码在继承页仍是旧的。
- 新增页沿用源页的导航高亮（应显示新章节或隐藏）。
- 改了 SVG 但忘记同步备注副本。
- 备注里描述的动画与实际 `animations.json` 不一致。
- 交付记录写入时间早于成品导出时间，导致记录对不上。
- 固定文件名被 PowerPoint 占用时覆盖失败；另存新版本，不杀用户进程。
