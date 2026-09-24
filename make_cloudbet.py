#!/usr/bin/env python3
"""Build the MVP x Cloudbet partner document from a pristine Mr-Q-2027 checkout.

- Partner logo, favicons and palette swapped MrQ -> Cloudbet
- Audience Demographics tab, its panel, the tab strip and all orphaned CSS/JS removed
- Editing controls (hint, Reset, Download HTML) and contenteditable hidden until
  Ctrl+Shift+E (Cmd+Shift+E on Mac) toggles edit mode; Download PDF always visible
Text replacements run only on segments outside base64 data URIs.
"""
import base64, hashlib, re, sys

SRC, OUT, CB = sys.argv[1], sys.argv[2], sys.argv[3]
h = open(SRC, encoding='utf-8').read()

def b64(path):
    return base64.b64encode(open(path, 'rb').read()).decode()

def once(s, old, new, label):
    n = s.count(old)
    assert n == 1, f'{label}: expected 1 match, found {n}'
    return s.replace(old, new)

# ---------- 1. Swap images by attribute anchor (payloads never touched by text ops)
def swap_uri(s, anchor, mime, data, label):
    pat = re.compile(re.escape(anchor) + r'"data:[^"]+"')
    s, n = pat.subn(lambda m: anchor + f'"data:{mime};base64,{data}"', s)
    assert n == 1, f'{label}: {n}'
    return s

h = swap_uri(h, 'sizes="32x32" href=', 'image/png', b64(f'{CB}/icon32.png'), 'fav32')
h = swap_uri(h, 'sizes="192x192" href=', 'image/png', b64(f'{CB}/icon192.png'), 'fav192')
h = swap_uri(h, 'sizes="180x180" href=', 'image/png', b64(f'{CB}/icon180.png'), 'fav180')
h = swap_uri(h, 'rel="shortcut icon" href=', 'image/x-icon', b64(f'{CB}/favicon.ico'), 'ico')
h = swap_uri(h, '<img class="midnite" src=', 'image/png', b64(f'{CB}/cloudbet_wordmark.png'), 'logo')
OLD_MVP = re.search(r'<img class="mvp" src="(data:[^"]+)"', h).group(1)

# ---------- 2. Split into text / base64 segments; edits only on text segments
parts = re.split(r'(data:[a-z/+\-]+;base64,[A-Za-z0-9+/=]+)', h)
text = ''.join(p if i % 2 == 0 else f'\x00{i}\x00' for i, p in enumerate(parts))

# 2a. Remove tab strip and audience panel
text, n = re.subn(r'\n  <div class="tabs no-print".*?</div>\n', '\n', text, flags=re.S); assert n == 1
text, n = re.subn(r'\n  <section class="panel is-active" data-tab="audience">.*?\n  </section>\n', '\n', text, flags=re.S); assert n == 1
text = once(text, '<section class="panel" data-tab="commercials">', '<section class="panel">', 'panel')

# 2b. CSS: replace everything from /* Tabs */ to </style> (tabs, metrics, channels,
#     demo blocks, chart — all audience-only) with the single-panel + edit-mode rules.
new_css = '''/* Single panel (Commercials) */
.panel { padding-top: 24px; }
.panel-head { margin-bottom: 20px; }
.panel-head h1 { margin: 0 0 4px; }

/* Edit mode — Ctrl+Shift+E. Hidden controls are out of layout entirely. */
body:not(.editing) .edit-only { display: none !important; }
.toolbar .kbd {
  font-family: 'Barlow Condensed', sans-serif; font-weight: 600;
  border: 1px solid var(--hair); border-radius: 3px; padding: 1px 5px;
  margin-left: 4px; color: var(--ink);
}
'''
text, n = re.subn(r'/\* Tabs \*/.*?(?=</style>)', new_css, text, flags=re.S); assert n == 1

# 2c. Palette: MrQ blue -> Cloudbet black
text = once(text, '--brand: #0a2ecc;', '--brand: #000000;', 'brand')
text = once(text, 'background: #08229a;', 'background: #2b2b2b;', 'hover')
text, n = re.subn(r'rgba\(10,46,204,', 'rgba(0,0,0,', text); assert n == 4, n
text = once(text, '.lockup img.midnite { height: 40px;', '.lockup img.partner { height: 21px;', 'css-logo')
text = once(text, '  .lockup img.midnite { height: 30px; }', '  .lockup img.partner { height: 15.5px; }', 'css-logo-print')
text = once(text, '<img class="midnite"', '<img class="partner"', 'img-class')

# 2d. Toolbar: mark editing controls
text = once(text, '<span class="hint">Click any text to edit · ',
            '<span class="hint edit-only">Editing on · click any text · <span class="kbd">Ctrl+Shift+E</span> to exit · ', 'hint')
text = once(text, '<button type="button" id="resetBtn">', '<button type="button" class="edit-only" id="resetBtn">', 'reset')
text = once(text, '<button type="button" id="htmlBtn">', '<button type="button" class="edit-only" id="htmlBtn">', 'htmlbtn')

# 2e. Partner naming
for old, new in [('MVP × MrQ — Partnership Document', 'MVP × Cloudbet — Partnership Document'),
                 ('alt="MrQ"', 'alt="Cloudbet"'),
                 ("var KEY = 'mvp-mrq-doc-v1';", "var KEY = 'mvp-cloudbet-doc-v1';")]:
    text = once(text, old, new, old)
text = text.replace('Mr Q', 'Cloudbet').replace('MrQ', 'Cloudbet')

# 2f. JS: editing no longer switched on unconditionally; tab code removed
text = once(text, '''  // Everything inside the sheet is editable except the logos.
  sheet.setAttribute('contenteditable', 'true');
  sheet.setAttribute('spellcheck', 'false');
''', '''  // Edit mode is off by default: no contenteditable, no editing controls.
  // Ctrl+Shift+E (Cmd+Shift+E on Mac) toggles it; the state lasts for the tab
  // session so a refresh mid-edit stays in edit mode.
  var MODEKEY = KEY + ':editing';
  function setEditing(on) {
    document.body.classList.toggle('editing', on);
    if (on) {
      sheet.setAttribute('contenteditable', 'true');
      sheet.setAttribute('spellcheck', 'false');
    } else {
      sheet.removeAttribute('contenteditable');
      sheet.removeAttribute('spellcheck');
      if (document.activeElement && sheet.contains(document.activeElement)) {
        document.activeElement.blur();
      }
      var sl = window.getSelection(); if (sl) { sl.removeAllRanges(); }
    }
    try { sessionStorage.setItem(MODEKEY, on ? '1' : '0'); } catch (e) {}
  }
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && !e.altKey &&
        (e.code === 'KeyE' || (e.key && e.key.toLowerCase() === 'e'))) {
      e.preventDefault();
      setEditing(!document.body.classList.contains('editing'));
    }
  });
''', 'edit-init')

text = once(text, '''  lockImages();
''', '''  lockImages();
  var startEditing = false;
  try { startEditing = sessionStorage.getItem(MODEKEY) === '1'; } catch (e) {}
  setEditing(startEditing);
''', 'edit-start')

text = once(text, '''  sheet.addEventListener('paste', function (e) {
    e.preventDefault();''', '''  sheet.addEventListener('paste', function (e) {
    if (!document.body.classList.contains('editing')) return;
    e.preventDefault();''', 'paste')

text = once(text, '''    // Always ship opening on the first tab, whatever is on screen here.
    var ts = Array.prototype.slice.call(clone.querySelectorAll('.tab'));
    ts.forEach(function (el, i) { el.setAttribute('aria-selected', String(i === 0)); });
    var ps = Array.prototype.slice.call(clone.querySelectorAll('.panel'));
    ps.forEach(function (el, i) { el.classList.toggle('is-active', i === 0); });

''', '''    // Always ship with edit mode off, whatever is on screen here.
    var b = clone.querySelector('body');
    if (b) { b.classList.remove('editing'); if (!b.className) b.removeAttribute('class'); }

''', 'export')

text, n = re.subn(r'\n  // Tab switching\..*?  show\(startTab\);\n', '\n', text, flags=re.S); assert n == 1

# 2g. Four placeholder assets (11-14) after Account Management, editable in edit mode
ASSET = '''
        <div class="terms-asset">
          <div class="terms-asset-num">{num}</div>
          <div class="terms-asset-body">
            <h4>Asset Title</h4>
            <ul>
              <li>Add detail</li>
              <li>Add detail</li>
            </ul>
          </div>
        </div>
'''
LAST = ('              <li>A dedicated MVP Account Director for the Term</li></ul>\n'
        '          </div>\n'
        '        </div>\n')
text = once(text, LAST, LAST + ''.join(ASSET.format(num=n) for n in ('11', '12', '13', '14')), 'new-assets')

# ---------- 3. Reassemble, stamp BUILD from content hash
out = re.sub(r'\x00(\d+)\x00', lambda m: parts[int(m.group(1))], text)
assert out.count('var BUILD = "dmufhhks8";') == 1
digest = hashlib.sha256(out.replace('var BUILD = "dmufhhks8";', '').encode()).hexdigest()[:10]
out = out.replace('var BUILD = "dmufhhks8";', f'var BUILD = "c{digest}";')
open(OUT, 'w', encoding='utf-8').write(out)

# ---------- 4. Checks
checks = []
def chk(name, cond): checks.append((name, bool(cond)))
nb = re.sub(r'data:[a-z/+\-]+;base64,[A-Za-z0-9+/=]+', 'DATA', out)
for bad in ['MrQ', 'Mr Q', 'Midnite', 'midnite', '0a2ecc', '08229a', '10,46,204',
            'data-tab', 'class="tab', 'Audience Demographics', 'Jake Paul', 'metric', '.channel', 'class="channel',
            '.ch-', 'class="ch-', 'demo-block', 'startTab', 'TABKEY', 'is-active', 'Venn']:
    chk(f'no "{bad}"', bad not in nb)
chk('Cloudbet present', nb.count('Cloudbet') >= 15)
chk('MVP logo untouched', OLD_MVP in out)
chk('5 base64 images + ico', len(re.findall(r'data:image/', out)) == 6)
for m in re.finditer(r'data:[a-z/+\-]+;base64,([A-Za-z0-9+/=]+)', out):
    try: base64.b64decode(m.group(1), validate=True); ok = True
    except Exception: ok = False
    chk(f'b64 decodes @{m.start()}', ok)
chk('pdfBtn not edit-only', re.search(r'<button[^>]*class="primary" id="pdfBtn"', out))
chk('3 edit-only controls', nb.count('edit-only') == 4)  # 3 in markup + 1 css rule
chk('keyboard handler', "e.code === 'KeyE'" in out)
chk('single panel', nb.count('<section class="panel">') == 1)
chk('14 assets', nb.count('class="terms-asset-num"') == 14)
chk('assets numbered 01-14 in order',
    re.findall(r'terms-asset-num">(\d+)<', nb) == [f'{i:02d}' for i in range(1, 15)])
chk('no sheet contenteditable in markup', 'id="sheet" contenteditable' not in out)
w = max(len(n) for n, _ in checks)
for n, ok in checks: print(f'  {"PASS" if ok else "FAIL"}  {n}')
fails = [n for n, ok in checks if not ok]
print(f'{len(checks) - len(fails)}/{len(checks)} checks passed · BUILD c{digest} · {len(out):,} bytes')
sys.exit(1 if fails else 0)
