"""Build the deployment book as one offline HTML file from its Markdown sources."""
import argparse
import base64
import html
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'docs/01-deployment-foundations'
REMOTE = 'https://github.com/qiyuefffs/llm-serving-diagnosis/blob/main/'


def slug(text):
    text = re.sub(r'<[^>]*>', '', text)
    text = text.replace('`', '').replace('*', '').lower()
    return re.sub(r'[^\w\-\s]', '', text, flags=re.UNICODE).replace(' ', '-')


def contents():
    entries = []
    group = '开始阅读'
    for line in (BOOK / 'SUMMARY.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            group = line[3:]
        match = re.match(r'(\s*)- \[([^]]+)\]\(([^)#]+\.md)\)', line)
        if match:
            entries.append({'path': match[3], 'label': match[2],
                            'group': group, 'depth': len(match[1]) // 2})
    return entries


def render_book():
    entries = contents()
    paths = ['README.md', 'SUMMARY.md']
    paths.extend(e['path'] for e in entries if e['path'] not in paths)
    # Each file has one authoritative reading position.
    paths = list(dict.fromkeys(paths))
    ids = {(BOOK / p).resolve(): f'ch{i:02}' for i, p in enumerate(paths)}
    md = MarkdownIt('commonmark', {'html': False}).enable('table')
    pages, search = [], []
    for i, relative in enumerate(paths):
        source = BOOK / relative
        page_id = ids[source.resolve()]
        text = source.read_text(encoding='utf-8')
        tokens = md.parse(text)
        counts = {}
        headings = []
        for j, token in enumerate(tokens):
            if token.type == 'heading_open':
                label = tokens[j + 1].content
                key = slug(label)
                count = counts.get(key, 0)
                counts[key] = count + 1
                anchor = key if count == 0 else f'{key}-{count}'
                token.attrSet('id', f'{page_id}--{anchor}')
                if token.tag in ('h2', 'h3'):
                    headings.append((label, f'{page_id}--{anchor}', token.tag))
            for child in token.children or []:
                if child.type not in ('link_open', 'image'):
                    continue
                attr = 'src' if child.type == 'image' else 'href'
                href = child.attrGet(attr)
                parsed = urlsplit(href or '')
                if not href or parsed.scheme or parsed.netloc:
                    continue
                target = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source.resolve()
                if child.type == 'image':
                    if not target.is_relative_to(BOOK) or not target.is_file():
                        raise ValueError(f'Image outside book or missing: {relative}')
                    mime = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
                    child.attrSet('src', f'data:{mime};base64,' + base64.b64encode(target.read_bytes()).decode('ascii'))
                    child.attrSet('loading', 'lazy')
                elif target in ids:
                    fragment = '--' + unquote(parsed.fragment) if parsed.fragment else ''
                    child.attrSet('href', '#' + ids[target] + fragment)
                elif target == BOOK / 'book.html':
                    child.attrSet('href', '#ch00')
                elif target.is_relative_to(ROOT):
                    child.attrSet('href', REMOTE + quote(target.relative_to(ROOT).as_posix()) +
                                  ('#' + parsed.fragment if parsed.fragment else ''))
        title = next(t.content for t in tokens if t.type == 'inline')
        body = md.renderer.render(tokens, md.options, {})
        local_toc = ''.join(f'<a class="toc-{level}" href="#{html.escape(anchor)}">{html.escape(label)}</a>'
                            for label, anchor, level in headings)
        source_link = REMOTE + quote(source.relative_to(ROOT).as_posix())
        pages.append(f'<section class="chapter" id="{page_id}" data-index="{i}" hidden>'
                     f'<div class="chapter-meta">大模型部署知识体系 · {i + 1:02} / {len(paths):02}'
                     f'<a href="{source_link}" target="_blank" rel="noreferrer">Markdown 源文</a></div>'
                     f'<details class="local-toc"><summary>页内目录 · {len(headings)} 项</summary>{local_toc}</details>'
                     f'<article>{body}</article></section>')
        plain = re.sub(r'^\s*```[^\n]*$', '', text, flags=re.M)
        search.append({'id': page_id, 'title': title, 'text': plain})
    nav = ['<a class="toc-link" href="#ch01">完整知识体系目录</a>']
    previous_group = None
    for entry in entries:
        if entry['group'] != previous_group:
            nav.append(f'<div class="nav-group">{html.escape(entry["group"])}</div>')
            previous_group = entry['group']
        nav.append(f'<a class="toc-link depth-{entry["depth"]}" href="#{ids[(BOOK / entry["path"]).resolve()]}">'
                   f'{html.escape(entry["label"])}</a>')
    template = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>大模型部署知识体系 · 离线检索</title><link rel="icon" href="data:,"><style>
:root{--ink:#202f31;--muted:#657475;--accent:#176d65;--paper:#fffefa;--line:#dfe6e2;--side:#f1f4ef}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font-family:"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}button,input{font:inherit}
.sidebar{position:fixed;inset:0 auto 0 0;width:298px;background:var(--side);border-right:1px solid var(--line);overflow:auto;padding:30px 22px 50px;z-index:5}
.eyebrow{font-size:11px;letter-spacing:2px;font-weight:700;color:var(--accent)}.brand{font-size:22px;line-height:1.5;font-weight:700;margin:12px 0 5px}.edition{font-size:12px;color:var(--muted);margin-bottom:22px}
#search{width:100%;border:1px solid #ccd8cf;border-radius:7px;background:var(--paper);padding:11px;color:var(--ink)}
.nav-group{font-size:12px;font-weight:700;color:var(--muted);margin:25px 0 9px;line-height:1.65}.toc-link{display:block;color:#3f5352;font-size:13px;line-height:1.65;padding:7px 10px;margin:2px 0;border-left:2px solid transparent;border-radius:0 5px 5px 0}.toc-link.depth-1{padding-left:22px;font-size:12px}.toc-link.active{background:#dfebe2;border-left-color:var(--accent);color:#134d48;font-weight:700}
main{margin-left:298px;padding:45px 56px 110px;max-width:1250px}.chapter{max-width:850px;margin:auto}.chapter-meta{font-size:12px;color:var(--muted);letter-spacing:1px;border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:36px}.chapter-meta a{float:right;letter-spacing:0}
article{font-size:16px;line-height:1.95;overflow-wrap:anywhere}article h1,article h2,article h3{scroll-margin-top:80px}article h1{font-size:32px;line-height:1.45;letter-spacing:.2px;margin:0 0 24px}article h2{font-size:23px;line-height:1.6;margin:46px 0 18px;padding-top:8px;border-top:1px solid var(--line)}article h3{font-size:19px;line-height:1.65;margin:30px 0 14px}article h4{font-size:17px}article p{margin:15px 0}article li{padding-left:3px;margin:7px 0}article ul,article ol{padding-left:26px}article strong{font-weight:650}article img{max-width:100%;height:auto;display:block;margin:25px auto;border:1px solid var(--line);border-radius:6px}
pre{background:#f0f3f1;border:1px solid var(--line);border-left:3px solid #73a193;border-radius:5px;padding:18px 20px;overflow-x:auto;line-height:1.7;font-size:13px;white-space:pre;max-width:100%}code{font-family:Consolas,"SFMono-Regular",monospace;font-size:.88em;background:#edf2ed;padding:2px 5px;border-radius:3px}pre code{background:none;padding:0;font-size:inherit}blockquote{border-left:3px solid #73a193;padding:3px 20px;color:#4e6260;background:#f5f7f2}
.table-scroll{overflow:auto;border:1px solid var(--line);border-radius:5px;margin:23px 0}table{width:100%;border-collapse:collapse;font-size:13px;line-height:1.8;min-width:530px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#eaf0e9;font-weight:650}tr:last-child td{border-bottom:0}tbody tr:nth-child(even){background:#f7f8f3}
.local-toc{margin:50px 0 25px;border-top:1px solid var(--line);padding-top:18px;font-size:13px;color:var(--muted)}.local-toc a{display:block;margin:9px 0}.local-toc summary{cursor:pointer}.reader-footer{position:fixed;bottom:0;left:298px;right:0;background:rgba(255,254,250,.97);border-top:1px solid var(--line);padding:15px 32px;display:flex;align-items:center;justify-content:space-between;gap:18px;font-size:13px;z-index:3}.reader-footer a{max-width:43%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.reader-footer span{font-size:11px;color:var(--muted)}.topbar{display:none}.search-results{max-width:850px;margin:auto}.search-card{display:block;border-bottom:1px solid var(--line);padding:20px 0}.search-card strong{display:block;font-size:18px}.search-card p{font-size:14px;color:var(--muted);line-height:1.9}.empty{padding:40px 0;color:var(--muted)}.overlay{display:none}
.local-toc{margin:0 0 30px;border:1px solid var(--line);border-radius:6px;padding:14px 18px;background:#f5f7f2}.local-toc a{line-height:1.65}.local-toc .toc-h3{padding-left:16px;font-size:12px}.toc-link.depth-2{padding-left:32px;font-size:12px}.reader-footer a{min-width:0;flex:1}.reader-footer span{flex-shrink:0;white-space:nowrap}#ch00 .local-toc{display:none}#ch00 article>p:first-of-type img{max-height:76vh;width:auto;object-fit:contain}
@media(min-width:1450px){main{margin-left:330px;padding-left:80px;padding-right:80px}.sidebar{width:330px}.reader-footer{left:330px}}
@media(max-width:900px){.sidebar{transform:translateX(-100%);transition:transform .2s;width:290px}.sidebar.open{transform:translateX(0)}main{margin-left:0;padding:85px 25px 100px}.topbar{display:flex;position:fixed;inset:0 0 auto;background:var(--paper);border-bottom:1px solid var(--line);padding:13px 20px;align-items:center;gap:18px;z-index:4;font-size:13px}.topbar button{border:1px solid var(--line);border-radius:5px;background:var(--side);padding:5px 12px;color:var(--ink)}.reader-footer{left:0;padding:14px 20px}.overlay.show{display:block;position:fixed;inset:0;background:#18282455;z-index:4}article{font-size:15px}article h1{font-size:26px}article h2{font-size:21px}pre{font-size:12px;padding:14px}.chapter-meta{margin-bottom:28px}}
@media print{.sidebar,.topbar,.reader-footer,.local-toc,.search-results{display:none!important}main{margin:0;padding:0;max-width:none}.chapter[hidden]{display:block!important}.chapter{max-width:none;break-before:page}.table-scroll{overflow:visible}pre{white-space:pre-wrap;overflow:visible}.chapter-meta{margin-top:20px}article{font-size:11pt}article h1{font-size:23pt}article h2{font-size:17pt}a{color:inherit}}
</style></head><body>
<div class="topbar"><button id="menu" aria-label="打开目录">目录</button><span>大模型部署知识体系</span></div>
<div class="overlay" id="overlay"></div><aside class="sidebar" aria-label="知识体系目录"><div class="eyebrow">DEPLOYMENT ENGINEERING</div><div class="brand">大模型部署<br>知识体系</div><div class="edition">硬件与运行时 · 模型与引擎 · 优化与交付</div>
<input id="search" aria-label="搜索知识体系" placeholder="搜索设备、参数、错误或命令…" type="search"><nav>__NAV__</nav></aside>
<main><div class="search-results" id="search-results" hidden aria-live="polite"></div>__PAGES__
<noscript>请启用浏览器JavaScript以使用章节导航，或直接阅读仓库Markdown。</noscript></main>
<footer class="reader-footer"><a id="prev" href="#ch00">上一项</a><span id="progress"></span><a id="next" href="#ch01">下一项</a></footer>
<script id="book-data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('book-data').textContent);
const chapters=[...document.querySelectorAll('.chapter')];
const search=document.getElementById('search'),results=document.getElementById('search-results');
const side=document.querySelector('.sidebar'),overlay=document.getElementById('overlay');
let current=0;
for(const table of document.querySelectorAll('table')){const wrap=document.createElement('div');wrap.className='table-scroll';table.replaceWith(wrap);wrap.append(table)}
function closeMenu(){side.classList.remove('open');overlay.classList.remove('show')}
document.getElementById('menu').onclick=()=>{side.classList.toggle('open');overlay.classList.toggle('show')};overlay.onclick=closeMenu;
function show(){
  const id=decodeURIComponent(location.hash.slice(1))||'ch00';
  const target=document.getElementById(id),page=target?.closest('.chapter')||chapters[0];
  current=Number(page.dataset.index);
  chapters.forEach(c=>c.hidden=c!==page);results.hidden=true;search.value='';
  document.querySelectorAll('.toc-link').forEach(a=>{const on=a.hash==='#'+page.id;a.classList.toggle('active',on);on?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current')});
  for(const [key,index] of [['prev',current-1],['next',current+1]]){const link=document.getElementById(key);link.style.visibility=data[index]?'visible':'hidden';if(data[index]){link.href='#'+data[index].id;link.textContent=(key==='prev'?'← ':'')+data[index].title+(key==='next'?' →':'')}}
  document.getElementById('progress').textContent=(current+1)+' / '+data.length;
  document.title=data[current].title+' · 大模型部署知识体系';closeMenu();
  requestAnimationFrame(()=>{if(target&&target!==page)target.scrollIntoView({block:'start'});else window.scrollTo(0,0)});
}
window.addEventListener('hashchange',show);
document.querySelector('nav').addEventListener('click',e=>{if(e.target.closest('a')){search.value='';show();closeMenu()}});
search.addEventListener('input',()=>{
  const query=search.value.trim().toLowerCase();if(!query){show();search.focus();return}
  chapters.forEach(c=>c.hidden=true);results.hidden=false;results.replaceChildren();
  const title=document.createElement('h1');title.textContent='全文搜索';results.append(title);
  const matches=data.filter(d=>d.text.toLowerCase().includes(query));
  const count=document.createElement('p');count.textContent='找到 '+matches.length+' 项资料';results.append(count);
  for(const d of matches){const link=document.createElement('a');link.className='search-card';link.href='#'+d.id;const h=document.createElement('strong');h.textContent=d.title;const p=document.createElement('p');const at=d.text.toLowerCase().indexOf(query);p.textContent='…'+d.text.slice(Math.max(0,at-45),at+150).replace(/[#*`]/g,'')+'…';link.append(h,p);link.onclick=()=>{search.value='';if(location.hash==='#'+d.id)show();closeMenu()};results.append(link)}
  window.scrollTo(0,0);
});
search.addEventListener('keydown',e=>{if(e.key==='Enter')closeMenu()});
document.addEventListener('keydown',e=>{if(e.target.matches('input,textarea'))return;if(e.key==='ArrowRight'&&data[current+1])location.hash=data[current+1].id;if(e.key==='ArrowLeft'&&data[current-1])location.hash=data[current-1].id});
show();
</script></body></html>'''
    payload = json.dumps(search, ensure_ascii=False).replace('<', '\\u003c')
    return template.replace('__NAV__', ''.join(nav)).replace('__PAGES__', ''.join(pages)).replace('__DATA__', payload), len(paths)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=BOOK / 'book.html')
    args = parser.parse_args()
    result, count = render_book()
    args.output.write_text(result, encoding='utf-8')
    print(f'Built {count} chapters; {len(result.encode("utf-8")):,} bytes; all book images embedded.')


if __name__ == '__main__':
    main()
