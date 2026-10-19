"""Local project helpers; semantic and visual review remain model responsibilities."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIRS = ['00_开始阅读', '01_论文原文', '02_精简汇报版', '03_详细精读版', '04_备课备注', '05_图表素材', '06_演示与来源', '07_验收', '08_可编辑工程']
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main', 'a': 'http://schemas.openxmlformats.org/drawingml/2006/main', 'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def load(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(str(Path(path).name) + ': top-level JSON must be an object')
    return data

def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)

def local(root, value):
    value = str(value)
    if not value or re.match(r'^(?:[a-zA-Z]:|[\\/]|[a-zA-Z]+:)', value):
        raise ValueError('Expected project-relative path: ' + value)
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path escapes project: ' + value)
    return path

def safe_archive_name(value):
    value = str(value)
    if '\\' in value or not value or value.startswith('/') or re.match(r'^[A-Za-z]:', value):
        raise ValueError('Unsafe archive member path: ' + value)
    parts = value.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('Unsafe archive member path: ' + value)
    return '/'.join(parts)

def review_inputs(root):
    files = [root / name for name in ['content.json', 'config.json', 'delivery.json', 'plans/brief.json', 'plans/detailed.json']]
    data = load(root / 'content.json')
    for kind in ['sources', 'figures']:
        rows = data.get(kind, [])
        if not isinstance(rows, list):
            raise ValueError(kind + ' must be an array')
        for row in rows:
            if not isinstance(row, dict) or not row.get('path'):
                raise ValueError(kind + ' entries must be objects with path')
            files.append(local(root, row['path']))
    for variant in ['brief', 'detailed']:
        plan = load(root / f'plans/{variant}.json')
        slides = plan.get('slides', [])
        if not isinstance(slides, list):
            raise ValueError(variant + ': slides must be an array')
        for slide in slides:
            if not isinstance(slide, dict) or not slide.get('note'):
                raise ValueError(variant + ': slide entries must be objects with note')
            files.append(local(root, slide['note']))
    config = load(root / 'config.json')
    for field in ['media_allowlist', 'external_allowlist']:
        entries = config.get(field, []) or []
        if not isinstance(entries, list):
            raise ValueError(field + ' must be an array')
        for permission in entries:
            if isinstance(permission, dict) and permission.get('evidence'):
                files.append(local(root, permission['evidence']))
    return sorted(set(files))

def review_hashes(root):
    return {str(p.relative_to(root)).replace('\\', '/'): sha(p) for p in review_inputs(root)}

def note_text(text):
    lines = []
    for line in text.splitlines():
        line = re.sub(r'^#+\s*', '', line.strip())
        line = re.sub(r'^-\s+', '• ', line)
        line = re.sub(r'\*\*(.+?)\*\*|__(.+?)__', lambda m: m.group(1) or m.group(2), line)
        lines.append(line)
    return normal('\n'.join(lines))

def path_like(text):
    text = re.sub(r'https?://[^\s"<>]+', '', text, flags=re.I)
    return bool(re.search(r'(?:file:/|(?<![A-Za-z0-9])[A-Za-z]:[\\/](?!/)|\\\\[^\\/\s"<>]+[\\/]|/(?:Users|home|private|tmp|mnt|var|opt|srv|root|Volumes|data)/)', text, re.I))

def normal(text):
    return re.sub(r'\s+', '', text.replace('\u00ad', ''))

def doctor(args):
    candidates = [args.ppt_master, os.environ.get('PPT_MASTER_ROOT'), str(ROOT.parent / 'ppt-master')]
    master = next((Path(x).resolve() for x in candidates if x and (Path(x) / 'SKILL.md').is_file()), None)
    lo = shutil.which('soffice')
    if not lo and os.name == 'nt':
        for base in [os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')]:
            if base and (Path(base) / 'LibreOffice/program/soffice.exe').is_file():
                lo = str(Path(base) / 'LibreOffice/program/soffice.exe')
                break
    return {'python': sys.version.split()[0], 'libraries': {x: bool(importlib.util.find_spec(x)) for x in ['pymupdf', 'PIL', 'yaml']}, 'ppt_master_candidate': str(master) if master else None, 'ppt_master_integrity': 'not-run; load skill and run its current guard', 'libreoffice': lo, 'pdftoppm': shutil.which('pdftoppm')}

def init(args):
    import pymupdf
    source = Path(args.pdf).resolve()
    target = Path(args.out).resolve()
    if target.exists():
        raise ValueError('Output already exists; choose a new run directory')
    if not source.is_file():
        raise ValueError('Source PDF missing')
    with pymupdf.open(source) as doc:
        if doc.needs_pass or len(doc) == 0:
            raise ValueError('Encrypted or empty PDF')
        pages = len(doc)
        texts = [p.get_text('text', sort=True) for p in doc]
        info = {'sha256': sha(source), 'pages': pages, 'characters_per_page': [len(t.strip()) for t in texts], 'low_text_pages': [i + 1 for i, t in enumerate(texts) if len(t.strip()) < 80], 'reading_order': 'unverified; inspect columns and equations'}
    target.mkdir(parents=True)
    for name in DIRS:
        (target / name).mkdir()
    for variant in ['brief', 'detailed']:
        (target / '04_备课备注' / variant).mkdir()
    (target / 'plans').mkdir()
    copy = target / '01_论文原文/source.pdf'
    shutil.copyfile(source, copy)
    if sha(copy) != info['sha256']:
        raise ValueError('Source copy hash mismatch')
    (target / '08_可编辑工程/extracted.txt').write_text('\n\n'.join(f'=== PDF physical page {i + 1} ===\n{t}' for i, t in enumerate(texts)), encoding='utf-8')
    save(target / '07_验收/input.json', info)
    save(target / 'config.json', {'schema_version': 1, 'language': 'zh-CN', 'brief_minutes': [15, 20], 'manual_advance': True, 'narration': False, 'object_animation': False, 'local_only': True})
    save(target / 'content.json', {'schema_version': 1, 'paper': {'title': '', 'type': '', 'source_id': 'paper'}, 'sources': [{'id': 'paper', 'path': '01_论文原文/source.pdf', 'sha256': info['sha256'], 'pages': pages}], 'units': [], 'claims': [], 'methods': [], 'figures': [], 'resources': [], 'coverage': {'abstract_complete': False, 'introduction_complete': False, 'body_inventory_complete': False, 'supplement_status': 'not-investigated', 'limitations': []}})
    for variant in ['brief', 'detailed']:
        save(target / f'plans/{variant}.json', {'variant': variant, 'slides': []})
    save(target / 'delivery.json', {'variants': [{'variant': v, 'pptx': f'{DIRS[i]}/paper_{v}.pptx', 'pdf': f'{DIRS[i]}/paper_{v}.pdf'} for v, i in [('brief', 2), ('detailed', 3)]]})
    save(target / '07_验收/reviews.json', {key: {'status': 'pending', 'reviewer': '', 'scope': '', 'evidence': [], 'issues': [], 'artifacts': {}} for key in ['content', 'visual']})
    (target / '00_开始阅读/阅读说明.md').write_text('# 论文双版本项目\n\n当前为初始化状态，尚未完成论文核验与PPT制作。\n\n精简汇报版用于约15–20分钟汇报；详细精读版用于备课与深入阅读。论文原文为首要依据。来源、证据与验收状态见content.json及07_验收。\n', encoding='utf-8')
    return {'project': str(target), 'source_hash_verified': True, 'pages': pages, 'low_text_pages': info['low_text_pages'], 'status': 'initialized-not-reviewed'}

def content_check(root):
    errors, warnings = [], []
    data = load(root / 'content.json')
    maps = {}
    for kind in ['sources', 'units', 'claims', 'methods', 'figures', 'resources']:
        rows = data.get(kind, [])
        if not isinstance(rows, list):
            errors.append(kind + ' must be an array')
            rows = []
        invalid = [i + 1 for i, row in enumerate(rows) if not isinstance(row, dict)]
        if invalid:
            errors.append(kind + ' entries must be objects at indexes: ' + ','.join(map(str, invalid)))
            rows = [row for row in rows if isinstance(row, dict)]
        invalid_ids = [i + 1 for i, row in enumerate(rows) if not isinstance(row.get('id'), str) or not row['id'].strip()]
        if invalid_ids:
            errors.append(kind + ': IDs must be non-empty strings at indexes: ' + ','.join(map(str, invalid_ids)))
            rows = [row for row in rows if isinstance(row.get('id'), str) and row['id'].strip()]
        ids = [r['id'] for r in rows]
        if len(set(ids)) != len(ids):
            errors.append(kind + ': duplicate IDs')
        maps[kind] = {r['id']: r for r in rows}
    if data.get('schema_version') != 1:
        errors.append('Unsupported schema_version')
    paper = data.get('paper', {})
    if not isinstance(paper, dict):
        errors.append('paper must be an object')
        paper = {}
    if not paper.get('title') or not paper.get('type'):
        errors.append('Paper title/type required')
    if not isinstance(paper.get('source_id'), str) or paper['source_id'] not in maps['sources']:
        errors.append('Paper source_id must reference a source')
    enums = {'units': ('kind', {'abstract', 'introduction', 'other'}), 'claims': ('kind', {'author_claim', 'result', 'author_interpretation', 'teaching', 'our_suggestion'}), 'resources': ('type', {'system_demo', 'generated_sample', 'stimulus', 'third_party'})}
    for kind, (field, values) in enums.items():
        for row in maps[kind].values():
            if row.get(field) not in values:
                errors.append(str(row.get('id')) + ': invalid ' + field)
    for s in maps['sources'].values():
        path = local(root, s.get('path', ''))
        if not path.is_file() or sha(path) != s.get('sha256'):
            errors.append('Source missing/hash changed: ' + str(s.get('id')))
        elif path.suffix.lower() == '.pdf':
            import pymupdf
            with pymupdf.open(path) as doc:
                if len(doc) != s.get('pages'):
                    errors.append('Source page count changed: ' + str(s.get('id')))
    required = {'units': ['quote', 'explanation', 'argument_role', 'section'], 'claims': ['text', 'kind', 'quote', 'boundary', 'section'], 'methods': ['purpose', 'input', 'procedure', 'measure', 'analysis', 'output'], 'figures': ['label', 'caption', 'question', 'reading', 'boundary']}
    for kind, fields in required.items():
        for row in maps[kind].values():
            name = str(row.get('id'))
            for field in fields:
                if not row.get(field):
                    errors.append(f'{name}: missing {field}')
            src = maps['sources'].get(row.get('source_id'))
            page = row.get('page')
            if not src or type(page) is not int or not 1 <= page <= src.get('pages', 0):
                errors.append(name + ': invalid source/page')
            if kind == 'figures':
                if row.get('scope') not in ['body', 'supplement']:
                    errors.append(name + ': invalid figure scope')
                if not local(root, row.get('path', '')).is_file():
                    errors.append(name + ': figure image missing')
                if not row.get('claim_ids'):
                    warnings.append(name + ': no linked claims; explain descriptive role')
                for cid in row.get('claim_ids', []):
                    if cid not in maps['claims']:
                        errors.append(name + ': unknown claim ' + cid)
    coverage = data.get('coverage', {})
    if not isinstance(coverage, dict):
        errors.append('coverage must be an object')
        coverage = {}
    for field in ['abstract_complete', 'introduction_complete', 'body_inventory_complete']:
        if coverage.get(field) is not True:
            errors.append('Unverified coverage: ' + field)
    for kind in ['abstract', 'introduction']:
        if not any(u.get('kind') == kind for u in maps['units'].values()):
            errors.append('No ' + kind + ' units; explain mapping for atypical paper')
    if not maps['claims'] or not maps['methods']:
        errors.append('Claims and method/evidence structure must not be empty')
    if coverage.get('supplement_status') in [None, '', 'not-investigated']:
        errors.append('Supplement coverage not investigated')
    if coverage.get('limitations'):
        warnings.extend(str(x) for x in coverage['limitations'])
    plans = {}
    for variant in ['brief', 'detailed']:
        plan = load(root / f'plans/{variant}.json')
        slides = plan.get('slides', [])
        if not isinstance(slides, list):
            errors.append(variant + ': slides must be an array')
            slides = []
        invalid = [i + 1 for i, slide in enumerate(slides) if not isinstance(slide, dict)]
        if invalid:
            errors.append(variant + ': slide entries must be objects at indexes: ' + ','.join(map(str, invalid)))
            slides = [slide for slide in slides if isinstance(slide, dict)]
        plans[variant] = slides
        if plan.get('variant') != variant or not slides:
            errors.append('Missing/invalid plan: ' + variant)
        ids = [s.get('id') for s in slides]
        if any(not isinstance(x, str) or not x.strip() for x in ids) or len(set(str(x) for x in ids)) != len(ids):
            errors.append(variant + ': slide IDs must be unique non-empty strings')
        titles = [normal(str(s.get('title', ''))) for s in slides]
        markers = [s.get('page_marker') for s in slides if s.get('page_marker')]
        if len(markers) != len(set(str(x) for x in markers)):
            errors.append(variant + ': page markers must be unique')
        for s, title in zip(slides, titles):
            if titles.count(title) > 1 and not s.get('page_marker'):
                errors.append(variant + ': repeated titles require unique visible page_marker: ' + str(s.get('id')))
        covered = {k: set() for k in ['units', 'claims', 'methods', 'figures']}
        for slide in slides:
            for field in ['title', 'job', 'role', 'note']:
                if not slide.get(field):
                    errors.append(variant + ': slide missing ' + field)
            for key, field in [('units', 'unit_ids'), ('claims', 'claim_ids'), ('methods', 'method_ids'), ('figures', 'figure_ids')]:
                references = slide.get(field, [])
                if not isinstance(references, list) or any(not isinstance(x, str) for x in references):
                    errors.append(f'{variant}/{slide.get("id")}: {field} must be an array of strings')
                    continue
                for ident in references:
                    if ident not in maps[key]:
                        errors.append(f'{variant}/{slide.get("id")}: unknown {key} {ident}')
                    covered[key].add(ident)
            if not slide.get('note'):
                continue
            note = local(root, slide['note'])
            if not note.is_file() or len(note.read_text(encoding='utf-8').strip()) < 80:
                errors.append(f'{variant}/{slide.get("id")}: missing/substantially empty notes')
        if variant == 'detailed':
            for ident, u in maps['units'].items():
                if u.get('kind') in ['abstract', 'introduction'] and ident not in covered['units']:
                    errors.append('Detailed missing original unit: ' + ident)
            for ident, fig in maps['figures'].items():
                if fig.get('scope') == 'body' and ident not in covered['figures']:
                    errors.append('Detailed missing body figure/table: ' + ident)
            for ident in maps['methods']:
                if ident not in covered['methods']:
                    errors.append('Detailed missing method: ' + ident)
    return {'status': 'failed' if errors else 'structural-check-passed', 'errors': errors, 'warnings': warnings, 'semantic_accuracy': 'not-certified', 'coverage_truth': 'human-declaration-not-independently-proven'}, data, plans

def part_rels(z, part):
    name = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if name not in z.namelist():
        return {}
    return {x.get('Id'): x.attrib for x in ET.fromstring(z.read(name))}

def resolve_part(part, target):
    return posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(part), target))

def pptx_info(path):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise ValueError('Broken ZIP entry: ' + bad)
        presentation = ET.fromstring(z.read('ppt/presentation.xml'))
        rels = part_rels(z, 'ppt/presentation.xml')
        slides, externals, embeds, sensitive = [], [], [], []
        for name in z.namelist():
            if name.endswith('.rels'):
                for row in ET.fromstring(z.read(name)):
                    if row.get('TargetMode') == 'External':
                        externals.append({'part': name, 'target': row.get('Target')})
            if name.startswith('ppt/embeddings/'):
                embeds.append(name)
            if name.endswith(('.xml', '.rels')):
                node = ET.fromstring(z.read(name))
                text = '\n'.join(value for element in node.iter() for value in [element.text or '', *element.attrib.values()])
                if path_like(text):
                    sensitive.append(name)
        for node in presentation.findall('p:sldIdLst/p:sldId', NS):
            relation = rels[node.get('{'+NS['r']+'}id')]
            part = resolve_part('ppt/presentation.xml', relation['Target'])
            xml = ET.fromstring(z.read(part))
            notes = []
            note_relations = [r for r in part_rels(z, part).values() if r.get('Type', '').endswith('/notesSlide')]
            titles = []
            for shape in xml.findall('.//p:sp', NS):
                ph = shape.find('p:nvSpPr/p:nvPr/p:ph', NS)
                if ph is not None and ph.get('type') in ['title', 'ctrTitle']:
                    titles.append(''.join(x.text or '' for x in shape.findall('.//a:t', NS)))
            for row in note_relations:
                if row.get('TargetMode') == 'External':
                    continue
                note_part = resolve_part(part, row['Target'])
                nx = ET.fromstring(z.read(note_part))
                for shape in nx.findall('.//p:sp', NS):
                    ph = shape.find('p:nvSpPr/p:nvPr/p:ph', NS)
                    if ph is not None and ph.get('type') in ['sldImg', 'sldNum', 'dt', 'hdr', 'ftr']:
                        continue
                    for para in shape.findall('.//a:p', NS):
                        notes.append(''.join(x.text or '' for x in para.findall('.//a:t', NS)))
            transition = xml.find('p:transition', NS)
            slides.append({'part': part, 'titles': titles, 'text': '\n'.join(t.text or '' for t in xml.findall('.//a:t', NS)), 'notes': '\n'.join(notes), 'notes_relationship_count': len(note_relations), 'hidden': xml.get('show') == '0', 'automatic_ms': transition.get('advTm') if transition is not None else None, 'object_timing': xml.find('p:timing', NS) is not None})
        metadata = {}
        if 'docProps/core.xml' in z.namelist():
            metadata = {x.tag.split('}')[-1]: x.text or '' for x in ET.fromstring(z.read('docProps/core.xml'))}
        media = [n for n in z.namelist() if n.startswith('ppt/media/') and not n.endswith('/')]
        content_types = ET.fromstring(z.read('[Content_Types].xml'))
        defaults = {x.get('Extension', '').lower(): x.get('ContentType', '') for x in content_types if x.tag.endswith('Default')}
        overrides = {x.get('PartName', '').lstrip('/'): x.get('ContentType', '') for x in content_types if x.tag.endswith('Override')}
        images, active_media = [], []
        media_candidates = set(media)
        for name in z.namelist():
            if name.endswith('/') or name == '[Content_Types].xml':
                continue
            mime = overrides.get(name, defaults.get(Path(name).suffix.lstrip('.').lower(), ''))
            if mime.startswith(('image/', 'audio/', 'video/')):
                media_candidates.add(name)
            elif not name.endswith(('.xml', '.rels')) and not mime.startswith('text/') and mime != 'application/vnd.openxmlformats-officedocument.presentationml.printerSettings':
                media_candidates.add(name)
        for name in sorted(media_candidates):
            mime = overrides.get(name, defaults.get(Path(name).suffix.lstrip('.').lower(), ''))
            (images if mime.startswith('image/') else active_media).append(name)
        media_hashes = {name: hashlib.sha256(z.read(name)).hexdigest() for name in active_media}
        xml_text = '\n'.join(z.read(n).decode('utf-8', errors='replace') for n in z.namelist() if n.endswith(('.xml', '.rels')))
    return {'slides': slides, 'external_relationships': externals, 'embeddings': embeds, 'local_path_parts': sensitive, 'media': active_media, 'media_hashes': media_hashes, 'images': images, 'comments': [n for n in z.namelist() if re.search(r'comment|person', n, re.I)], 'metadata': metadata, 'xml_text': xml_text}

def reviewed_permissions(root, config, info, variant):
    errors = []
    for field, actual in [('media_allowlist', info['media']), ('external_allowlist', [x['target'] for x in info['external_relationships']])]:
        entries = config.get(field, [])
        if not isinstance(entries, list):
            errors.append(variant + ': ' + field + ' must be an array')
            continue
        for item in actual:
            matches = [x for x in entries if isinstance(x, dict) and x.get('variant') == variant and x.get('target') == item]
            if len(matches) != 1:
                errors.append(variant + ': permission entry must have exactly one match for ' + field + ' target: ' + str(item))
                continue
            row = matches[0]
            if field == 'media_allowlist' and row.get('target_sha256') != info['media_hashes'].get(item):
                errors.append(variant + ': media permission missing/stale target_sha256: ' + str(item))
            if not row.get('reviewer') or row.get('status') != 'pass' or not row.get('evidence'):
                errors.append(variant + ': unreviewed ' + field + ' target: ' + str(item))
                continue
            evidence = local(root, row['evidence'])
            if not evidence.is_file():
                errors.append(variant + ': missing permission/playback evidence: ' + row['evidence'])
            elif row.get('evidence_sha256') != sha(evidence):
                errors.append(variant + ': stale permission/playback evidence: ' + row['evidence'])
    return errors

def delivery_check(root):
    import pymupdf
    base, data, plans = content_check(root)
    errors, warnings = list(base['errors']), list(base['warnings'])
    rows, hashes = [], {}
    variants = load(root / 'delivery.json').get('variants', [])
    if not isinstance(variants, list) or any(not isinstance(x, dict) for x in variants):
        errors.append('Delivery variants must be an array of objects')
        variants = [x for x in variants if isinstance(x, dict)] if isinstance(variants, list) else []
    if sorted(x.get('variant', '') for x in variants) != ['brief', 'detailed']:
        errors.append('Delivery must contain exactly brief and detailed')
    config = load(root / 'config.json')
    for v in variants:
        if not all(v.get(key) for key in ['variant', 'pptx', 'pdf']):
            errors.append('Delivery variant missing variant/pptx/pdf')
            continue
        variant = v['variant']
        if variant not in plans:
            errors.append('Unknown delivery variant: ' + str(variant))
            continue
        pptx, pdf = local(root, v['pptx']), local(root, v['pdf'])
        if not pptx.is_file() or not pdf.is_file():
            errors.append(variant + ': exported PPTX/PDF missing')
            continue
        info = pptx_info(pptx)
        with pymupdf.open(pdf) as doc:
            pdf_count = len(doc)
            pdf_pages = [p.get_text() for p in doc]
            pdf_text = '\n'.join(pdf_pages)
        hashes[v['pptx']], hashes[v['pdf']] = sha(pptx), sha(pdf)
        if not len(info['slides']) == pdf_count == len(plans[variant]):
            errors.append(variant + ': PPTX/PDF/plan page mismatch')
        for i, slide in enumerate(info['slides']):
            if slide['notes_relationship_count'] != 1:
                errors.append(f'{variant} page {i+1}: expected exactly one notes relationship')
            if len(slide['notes'].strip()) < 80:
                errors.append(f'{variant} page {i+1}: missing/empty embedded notes')
            if i < len(plans[variant]):
                planned = plans[variant][i]
                note_path = local(root, planned['note'])
                if note_path.is_file() and note_text(note_path.read_text(encoding='utf-8')) != normal(slide['notes']):
                    errors.append(f'{variant} page {i+1}: embedded note differs from Markdown')
                title = normal(planned['title'])
                if slide['titles'] != []:
                    if len(slide['titles']) != 1 or normal(slide['titles'][0]) != title:
                        errors.append(f'{variant} page {i+1}: title/order differs from plan')
                else:
                    errors.append(f'{variant} page {i+1}: native title placeholder required for order verification')
                marker = planned.get('page_marker')
                if marker:
                    marker = str(marker)
                    if marker not in slide['text'] or i >= pdf_count or marker not in pdf_pages[i]:
                        errors.append(f'{variant} page {i+1}: unique page marker missing or out of order in PPTX/PDF')
                if i < pdf_count and title not in normal(pdf_pages[i]):
                    errors.append(f'{variant} page {i+1}: PDF title differs from plan or is not extractable')
            if slide['hidden']:
                errors.append(f'{variant} page {i+1}: hidden slide')
            if config.get('manual_advance', True) and slide['automatic_ms'] is not None:
                errors.append(f'{variant} page {i+1}: automatic advance')
            if not config.get('object_animation', False) and slide['object_timing']:
                errors.append(f'{variant} page {i+1}: unexpected object timing')
            if re.search(r'\{\{[A-Z_0-9]+\}\}', slide['text']):
                errors.append(f'{variant} page {i+1}: unresolved placeholder')
        if info['embeddings']:
            errors.append(variant + ': embedded objects are not permitted by default')
        if info['local_path_parts']:
            errors.append(variant + ': local paths detected in package XML')
        if info['comments']:
            errors.append(variant + ': comments/person parts detected')
        errors.extend(reviewed_permissions(root, config, info, variant))
        sensitive_terms = config.get('sensitive_terms', [])
        if not isinstance(sensitive_terms, list) or any(not isinstance(t, str) or not t.strip() for t in sensitive_terms):
            errors.append('sensitive_terms must be an array of non-empty strings')
        else:
            hits = [t for t in sensitive_terms if t.casefold() in (info['xml_text'] + '\n' + pdf_text).casefold()]
            if hits:
                errors.append(variant + ': sensitive terms detected: ' + ', '.join(hits))
        all_text = '\n'.join(x['text'] for x in info['slides'])
        if variant == 'detailed':
            for unit in data['units']:
                if unit.get('kind') == 'abstract' and normal(unit['quote']) not in normal(all_text + pdf_text):
                    warnings.append(unit['id'] + ': abstract not extractable as text; inspect screenshot evidence')
        rows.append({'variant': variant, 'slides': len(info['slides']), 'pdf_pages': pdf_count, 'externals': info['external_relationships'], 'metadata': info['metadata']})
    try:
        input_hashes = review_hashes(root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        input_hashes = {}
        errors.append('Cannot bind review inputs: ' + str(exc))
    reviews = load(root / '07_验收/reviews.json')
    pending = []
    for kind in ['content', 'visual']:
        review = reviews.get(kind, {})
        if review.get('status') == 'fail':
            errors.append(kind + ' review failed')
        elif review.get('status') != 'pass':
            pending.append(kind)
        else:
            if not all(review.get(x) for x in ['reviewer', 'scope', 'evidence', 'artifacts']) or review.get('issues'):
                errors.append(kind + ': invalid pass record or unresolved issues')
            for artifact, digest in input_hashes.items():
                if review.get('artifacts', {}).get(artifact) != digest:
                    errors.append(kind + ': review missing/stale for input ' + artifact)
            for artifact, digest in hashes.items():
                if review.get('artifacts', {}).get(artifact) != digest:
                    errors.append(kind + ': review missing/stale for delivery ' + artifact)
            for evidence in review.get('evidence', []):
                if not local(root, evidence).is_file():
                    errors.append(kind + ': missing evidence file ' + evidence)
    status = 'blocked' if errors else 'unverified' if pending else 'passed-with-limitations' if warnings else 'passed'
    return {'status': status, 'errors': errors, 'warnings': warnings, 'pending_reviews': pending, 'variants': rows, 'artifact_hashes': hashes, 'input_hashes': input_hashes, 'note': 'Program checks do not prove semantic accuracy or visual readability'}

def audit(args):
    info = pptx_info(Path(args.pptx))
    findings = []
    if info['media']: findings.append('Audio/video or unknown binary parts require review')
    if info['external_relationships']: findings.append('External relationships')
    if info['embeddings']: findings.append('Embedded payloads')
    if info['local_path_parts']: findings.append('Local paths')
    if info['comments']: findings.append('Comments/person parts')
    if any(s['hidden'] for s in info['slides']): findings.append('Hidden slides')
    if any(s['notes'].strip() for s in info['slides']): findings.append('Notes require privacy review')
    text = '\n'.join(s['text'] + '\n' + s['notes'] for s in info['slides'])
    # Scan every XML part, including master/layout text and custom properties.
    with zipfile.ZipFile(args.pptx) as z:
        text += '\n' + '\n'.join(z.read(n).decode('utf-8', errors='replace') for n in z.namelist() if n.endswith(('.xml', '.rels')))
    hits = [term for term in args.term if term.casefold() in text.casefold()]
    if hits: findings.append('Matched user-defined sensitive terms')
    return {'status': 'needs-review' if findings else 'automated-scan-clean', 'findings': findings, 'term_hits': hits, 'metadata': info['metadata'], 'media': info['media'], 'external_relationships': info['external_relationships'], 'embeddings': info['embeddings'], 'local_path_parts': info['local_path_parts'], 'limits': 'Not OCR/image inspection; cannot certify licenses or absence of personal images'}

def package(args):
    dest = Path(args.out).resolve()
    if dest.exists():
        raise ValueError('Package already exists')
    manifest = load(ROOT / 'share-manifest.json')
    allowed = manifest.get('files', [])
    if not isinstance(allowed, list) or not allowed or len(set(allowed)) != len(allowed):
        raise ValueError('Share manifest must be a non-empty unique file list')
    paths = []
    template_root = 'assets/neutral-academic_20261017/'
    for name in allowed:
        name = safe_archive_name(name)
        permitted = (name in {'SKILL.md', 'README.md', 'LICENSE.txt', 'share-manifest.json'}
                     or name.startswith(('references/', 'examples/')) and Path(name).suffix == '.md'
                     or name.startswith('scripts/') and Path(name).suffix == '.py'
                     or name.startswith(template_root + 'templates/') and Path(name).suffix in {'.md', '.svg'}
                     or name == template_root + 'exports/neutral-academic_template_preview.pptx')
        if not permitted:
            raise ValueError('File outside share policy: ' + name)
        path = local(ROOT, name)
        if not path.is_file(): raise ValueError('Missing shared file: ' + name)
        if path.suffix.lower() in ['.pdf', '.env', '.log'] or '__pycache__' in path.parts or any(part in ['local-validation', 'paper-dual-ppt-delivery'] for part in path.parts):
            raise ValueError('Disallowed shared file: ' + name)
        paths.append((name, path))
    for name, path in paths:
        if path.suffix.lower() in {'.md', '.svg', '.txt', '.json'}:
            text = path.read_text(encoding='utf-8', errors='replace')
            if path_like(text):
                raise ValueError('Sensitive absolute path in shared file: ' + name)
        elif path.suffix.lower() == '.pptx':
            info = pptx_info(path)
            if info['external_relationships'] or info['embeddings'] or info['local_path_parts'] or info['comments'] or info['media']:
                raise ValueError('Unsafe content in shared PPTX: ' + name)
            if any(value.strip() for key, value in info['metadata'].items() if key in {'creator', 'lastModifiedBy'}):
                raise ValueError('Personal metadata in shared PPTX: ' + name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.paper-dual-', suffix='.zip', dir=dest.parent, delete=False) as stream:
            staged = Path(stream.name)
        with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, path in paths:
                z.write(path, 'paper-dual-ppt/' + name)
        with staged.open('rb') as source, dest.open('xb') as target:
            try:
                shutil.copyfileobj(source, target)
            except BaseException:
                target.close()
                dest.unlink(missing_ok=True)
                raise
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return {'zip': str(dest), 'files': len(paths), 'sha256': sha(dest)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    d = sub.add_parser('doctor'); d.add_argument('--ppt-master')
    i = sub.add_parser('init'); i.add_argument('--pdf', required=True); i.add_argument('--out', required=True)
    for name in ['check-content', 'check-delivery']:
        s = sub.add_parser(name); s.add_argument('project'); s.add_argument('--report')
    a = sub.add_parser('audit-template'); a.add_argument('pptx'); a.add_argument('--term', action='append', default=[]); a.add_argument('--report')
    s = sub.add_parser('package'); s.add_argument('--out', required=True)
    args = p.parse_args()
    try:
        if args.command == 'doctor': result = doctor(args)
        elif args.command == 'init': result = init(args)
        elif args.command == 'check-content': result = content_check(Path(args.project).resolve())[0]
        elif args.command == 'check-delivery': result = delivery_check(Path(args.project).resolve())
        elif args.command == 'audit-template': result = audit(args)
        else: result = package(args)
        if getattr(args, 'report', None): save(args.report, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('errors') or result.get('status') in ['needs-review', 'failed', 'blocked', 'unverified'] else 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
