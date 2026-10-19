# 图表与原文截图的图片版式

论文讲解必须放真实图片：论文 Figure、表格截图、摘要标色截图。但**不能把图片塞进文本槽**。本文件说明正确做法，避免依赖报错、避免槽位契约被破坏。

## 1. 为什么不能塞进文本槽

结构化模板中，每个 slot 的占位符类型是固定契约：

| 槽位类型 | 合法载体 |
|---|---|
| `title` / `subtitle` / `body` | 一个 `<text data-pptx-carrier="true">` |
| `picture` / `media` | 一个 `<image>`（标记为 carrier） |
| `object` | 文本、图片、基本形状或紧凑 authored-preset `<g>`，或 `binding="proxy"` 的复合槽 |

把 `<image>` 放进 `body` 槽会破坏该 Layout 的槽位契约：同一 Layout 的所有页面必须保持相同的 slot id、类型、索引、边界与绑定方式。导出器不会替你「猜」这是一张图，校验会报 `placeholder 'body' must be carried by one direct <text> child` 之类的错误。

## 2. 三种合法做法

按优先级选择：

1. **新增带 picture 槽的 Layout**（推荐，适合长期复用）  
   在模板工作区新增一个原型，例如「宽图 + 下方读法」「截图 + 编号解释」。需要在 Design Spec §V 增加一行，并在各工程的 `spec_lock.md` 中声明 `pptx_layouts` 与 `page_pptx_layouts`。
2. **在现有 Layout 新增一个 picture 槽**  
   仅当该 Layout 下所有页面都需要这个槽时才成立；槽位集合按 Layout 共享，不能只给某一页加。
3. **改为 Slide-local 内容**  
   该页若确实不属于结构化槽位，可把图片作为页面本地内容放置：一个根级 `<g>` 带页面坐标 `data-pptx-bounds`，内部放 `<image href="../images/...">`，不与槽位内容重叠。这不需要原型声明 picture 槽，也不会报错；但此时它不承载任何占位符，不要声称它是槽位内容。

不可行的做法：把图片伪装成文本、把图片截成字符画、用示意图替代原图、把原图缩到看不清再硬塞。

## 2.1 合法槽位类型与载体

| 槽位类型 | 合法载体 | PowerPoint 占位符 |
|---|---|---|
| `title` / `subtitle` / `body` | 一个 `<text data-pptx-carrier="true">` | `title` / `subTitle` / `body` |
| `picture` | 一个 `<image data-pptx-carrier="true">`（推荐） | `pic` |
| `media` | 一个 `<image>`；只承载画面，不合成音视频 | `media` |
| `object` | 文本、图片、基本形状或紧凑 authored-preset `<g>`，或声明 `binding="proxy"` 的复合槽 | `obj` |

想让图片在 PowerPoint 里成为真正的图片占位符，用 `picture`，不要用 `object`。

picture 槽的写法（槽 `<g>` 是根级直接子元素，只带 `id` 与 `data-pptx-*`）：

```xml
<g id="picture-slot" data-pptx-placeholder="picture" data-pptx-idx="2"
   data-pptx-bounds="64 120 752 500">
  <image id="picture-carrier" data-pptx-carrier="true"
         x="64" y="120" width="752" height="500"
         preserveAspectRatio="xMidYMid meet"
         href="../images/fig5.png"/>
</g>
```

- 槽的 `data-pptx-bounds` 是可复用设计区；carrier 的 `x/y/width/height` 是本页可见几何，可以与槽默认框不同。
- `data-pptx-frame` 只由 preset helper 写，手写会让校验失败；普通内容组不要用它。
- 模板原型里常用 1×1 的 base64 图片当中性占位，这是模板侧做法；项目页面应引用 `../images/` 下的真实文件。

## 3. 新增 Layout 时要同步的文件

一次改动必须同时落在这几处，否则校验或导出会失败：

| 文件 | 内容 |
|---|---|
| `templates/design_spec.deck.<id>.md` | §V 增加原型行：Layout key、picker 名、槽位、容量、字体 |
| `templates/<新原型>.svg` | 完整页面原型，根节点带 Master/Layout 身份 |
| 各工程 `spec_lock.md` | `pptx_masters`、`pptx_layouts`、`page_pptx_layouts`、`page_layouts` |
| 各工程 `design_spec.md` §VIII | 图片资源行：文件名、尺寸、用途、crop 策略、来源 |

## 4. 图片资源准备

- 从论文 PDF 裁图时保留轴、图例、脚注与单位；裁切完整性要逐张看过，不能只看尺寸。
- 表格截图优先保留列名与单位；过宽时拆成多行或横向分片，但每片都要能读出对应列。
- 摘要标色截图：编号与颜色同时对应，颜色之外必须还有编号。
- 图片放在工程 `images/` 下，SVG 用相对路径 `../images/<name>` 引用。
- 不得把论文截图上传到外部服务；本地裁图即用。

## 5. 版面要求

- 图片区域内不叠正文；说明文字放在图下方或右侧栏。
- 右栏说明不得长到超过图片高度的一半以下才开始，必要时把说明拆成两条。
- 图片按 `meet`（完整显示）放置时，容器余白由版面吸收，不用拉伸；按 `slice`（填充裁切）时必须确认关键内容没被裁掉。
- 图注与页脚不重复同一信息。

## 6. 校验

导出前至少确认：

- 放图片的槽只有一种走法：已声明的 picture 槽，或 Slide-local；没有把 `<image>` 放进 title/subtitle/body 槽；
- 同一 Layout 的各页槽位 id、类型、索引、边界与绑定方式一致；页面没有自行新增原型未声明的槽；
- 图片作为固定 `data-pptx-layer="layout"` 原子时，每页内容相同；会变的图片放槽或留在页面本地；
- 图片文件存在、有显式正 `width`/`height`、只有一个非空 `href`、`preserveAspectRatio` 拼写合法；
- 页面本地图片没有与槽位内容重叠；
- 最终 PDF 中图片清晰、未变形、未裁掉关键部分。
