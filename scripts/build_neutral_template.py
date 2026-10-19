"""Build the original neutral template into a preinitialized, empty template directory."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as E

S = 'http://www.w3.org/2000/svg'
E.register_namespace('', S)
BLUE, INK, GRAY, PALE = '#285A9F', '#172B46', '#53657A', '#EDF3FA'

def add(parent, tag, attrs, text=None):
    node = E.SubElement(parent, '{'+S+'}'+tag, {k: str(v) for k, v in attrs.items()})
    node.text = text
    return node

def slot(root, ident, role, bounds, marker, size=28, color=INK, idx=None):
    x, y, w, h = bounds
    a = {'id': ident, 'data-pptx-placeholder': role, 'data-pptx-bounds': f'{x} {y} {w} {h}'}
    if idx is not None: a['data-pptx-idx'] = idx
    g = add(root, 'g', a)
    attrs = {'id': ident+'-carrier', 'data-pptx-carrier': 'true', 'x': x, 'y': y+size, 'fill': color}
    if size != 28: attrs['font-size'] = size
    add(g, 'text', attrs, marker)

def root_page(key, name):
    r = E.Element('{'+S+'}svg', {'viewBox': '0 0 1280 720', 'font-family': 'Arial, Microsoft YaHei, sans-serif', 'font-size': '28', 'data-pptx-master': 'academic-master', 'data-pptx-master-name': 'Neutral Academic', 'data-pptx-layout': key, 'data-pptx-layout-name': name})
    common = {'data-pptx-layer': 'master', 'data-pptx-editable': 'false'}
    add(r, 'rect', dict(common, id='background', x=0, y=0, width=1280, height=720, fill='#FFFFFF'))
    add(r, 'rect', dict(common, id='accent', x=56, y=48, width=50, height=5, fill=BLUE))
    add(r, 'line', dict(common, id='footer-line', x1=56, y1=663, x2=1224, y2=663, stroke='#D8E2EE', **{'stroke-width': 1}))
    return r

def build(dest, force=False):
    dest = Path(dest).resolve()
    templates = dest / 'templates'
    if not dest.is_dir(): raise ValueError('Initialize project with ppt-master first')
    if templates.exists() and any(templates.iterdir()) and not force: raise ValueError('Templates not empty')
    templates.mkdir(exist_ok=True)
    pages = []
    def finish(stem, name, r, markers, description):
        E.ElementTree(r).write(templates / (stem+'.svg'), encoding='utf-8', xml_declaration=True)
        pages.append((stem, name, markers, description))
    r = root_page('cover', '论文封面与路线')
    slot(r,'title','title',(64,150,1152,160),'{{TITLE}}',48,BLUE)
    slot(r,'subtitle','subtitle',(64,340,1152,100),'{{SUBTITLE}}',28)
    slot(r,'author','body',(64,520,1152,90),'{{AUTHOR}}',22,GRAY,2)
    finish('01_cover','论文封面与路线',r,['TITLE','SUBTITLE','AUTHOR'],'上部双行标题，中部论文定位，下部作者/路线；48/28/22px，标题区160高')
    r = root_page('chapter', '章节与论证任务')
    slot(r,'chapter-num','body',(64,170,180,120),'{{CHAPTER_NUM}}',64,BLUE,1)
    slot(r,'chapter-title','title',(280,180,936,130),'{{CHAPTER_TITLE}}',44)
    slot(r,'chapter-desc','body',(280,360,936,180),'{{CHAPTER_DESC}}',28,GRAY,2)
    finish('02_chapter','章节与论证任务',r,['CHAPTER_NUM','CHAPTER_TITLE','CHAPTER_DESC'],'左侧章节编号，右侧标题/任务；非时间线，不暗示因果')
    variants = [
        ('03a_content_quote','quote','原文与解释',[(64,210,540,400),(660,210,556,400)],['ORIGINAL','EXPLANATION'],'左英文摘录/截图区域，右概括与边界；各列400高，原图可作为Slide-local替代内容而非强塞文本槽'),
        ('03b_content_flow','flow','证据获取流程',[(64,205,1152,155),(64,405,1152,205)],['PROCEDURE','MEASUREMENT'],'上部流程，下部测量与证据；不预设参与者/实验类型'),
        ('03c_content_compare','compare','方案或结论边界对照',[(64,210,350,400),(464,210,350,400),(864,210,352,400)],['COLUMN_1','COLUMN_2','COLUMN_3'],'三个对照对象，等宽只表达并列，不预设优劣；28px'),
        ('03d_content_evidence','evidence','图表与结论',[(64,210,760,400),(880,210,336,400)],['FIGURE_AREA','READING'],'左大图/表区域，右读法与结论边界；原图使用图片时按实际布局声明picture或允许的Slide-local内容，不以占位文本冒充图片')]
    for stem,key,name,bounds,markers,desc in variants:
        r = root_page(key,name)
        slot(r,'page-title','title',(64,83,1152,105),'{{PAGE_TITLE}}',38,BLUE)
        for i,(box,mark) in enumerate(zip(bounds,markers),1):
            slot(r,'body-'+str(i),'body',box,'{{'+mark+'}}',28,INK,i)
        slot(r,'source','footer',(64,677,1030,32),'{{SOURCE}}',16,GRAY)
        slot(r,'page-number','slide-number',(1150,677,66,32),'{{PAGE_NUM}}',16,GRAY)
        finish(stem,name,r,['PAGE_TITLE']+markers+['SOURCE','PAGE_NUM'],desc)
    r = root_page('ending','结论与讨论')
    slot(r,'ending-title','title',(64,125,1152,100),'{{THANK_YOU}}',44,BLUE)
    slot(r,'ending-body','body',(64,300,1152,300),'{{CLOSING_MESSAGE}}',30)
    slot(r,'page-number','slide-number',(1150,677,66,32),'{{PAGE_NUM}}',16,GRAY)
    finish('04_ending','结论与讨论',r,['THANK_YOU','CLOSING_MESSAGE','PAGE_NUM'],'上部总结标题，下部核心结论/讨论；不含联系信息或个人身份')
    fm = ['---','deck_id: neutral-academic','kind: deck','category: scenario','summary: 论文课堂讲解与原文精读，支持研究方法、证据和结论边界说明','keywords: [paper, evidence, teaching, reading]','primary_color: "#285A9F"','canvas_format: ppt169','canvas_width: 1280','canvas_height: 720','canvas_viewbox: "0 0 1280 720"','replication_mode: standard','native_structure_mode: structured','page_count: '+str(len(pages)),'placeholders:']
    for stem,_,markers,_ in pages:
        fm.append('  '+stem+': ['+', '.join('"{{'+m+'}}"' for m in markers)+']')
    fm += ['---','','# Neutral Academic — Design Specification','','## I. Template Overview','','论文课堂讲解、自学备课和证据精读。受众为初读论文的师生；原文对照与方法流程是代表性场景，不规定下游页序和页数。白底蓝色强调，无学校/作者身份资产。画布16:9，1280×720。','','## II. Color Scheme','','| Role | HEX |','|---|---|','| Primary | #285A9F |','| Text | #172B46 |','| Secondary | #53657A |','| Rule | #D8E2EE |','| Background | #FFFFFF |','','## III. Typography','','Latin Arial；EA Microsoft YaHei；均不嵌入/附送字体文件。目标为安装相应字体的Windows PowerPoint，其他机器需复核替代字体并使用PDF备份。标题38–48px、正文28–30px、来源16px为模板样例；实际项目按阅读距离调整。','','## IV. Signature Design Elements','','单一academic-master，左上短蓝线与底部分隔线作为跨页定位。正文左右不等宽与并列三栏分别服务原文/读法和方案对照，不引入固定统计或学科符号。矩形画布留白优于书页折角等暗示文档身份的装饰；分组通过轴线与留白表达，避免伪流程箭头。每个Layout槽位起点左上；来源与页码分开。无图片、图标、嵌入文件和外链。','','## V. Page Roster','','| Prototype | Layout key / picker | Slots and capacity / character |','|---|---|']
    for stem,name,markers,desc in pages:
        fm.append('| `'+stem+'.svg` | '+({'01_cover':'cover','02_chapter':'chapter','04_ending':'ending'}.get(stem,stem.split('_')[-1]))+' / '+name+' | '+desc+'；slots: '+', '.join(markers)+'；Arial/微软雅黑，左上换行 |')
    (templates/'design_spec.deck.neutral-academic.md').write_text('\n'.join(fm)+'\n',encoding='utf-8')
    return len(pages)

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('workspace'); p.add_argument('--force',action='store_true'); a=p.parse_args()
    print('Created prototypes:',build(a.workspace,a.force))
