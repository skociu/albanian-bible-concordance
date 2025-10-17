﻿function cleanText(s){
  try { return String(s||'').replace(/\\\"/g,'"').replace(/\\'/g,"'"); } catch(e){ return String(s||''); }
}// Clean, unified UI script (search + browse)

function sanitizeVerseText(s){
  try {
    let t = cleanText(s);
    // Remove prefixed debug markers such as "aaa see" or "aaa eee" (sometimes followed by an extra 'I')
    t = t.replace(/^\s*aaa\s+(see|eee)\s*I?\s+/i, '');
    return t;
  } catch (e) {
    return cleanText(s);
  }
}
const state = { books: null, verses: null, cache: {}, chaptersByBook: null, searchInterlinearOn: false, lastRefs: null, lastQuery: '' };

function normalizeToken(s) {
  return (s || '')
    .toLowerCase()
    .replace(/[��]/g, 'e')
    .replace(/[��]/g, 'c');
}

async function loadBooks() {
  if (state.books) return state.books;
  const res = await fetch('data/books.json');
  state.books = await res.json();
  return state.books;
}

async function loadVerses() {
  if (state.verses) return state.verses;
  const res = await fetch('data/verses.json');
  state.verses = await res.json(); try { state.verses = (state.verses||[]).map(r => Array.isArray(r) && r.length>3 ? [r[0], r[1], r[2], sanitizeVerseText(r[3])] : r); } catch(e){}
  return state.verses;
}

async function loadIndexShard(letter) {
  if (state.cache[letter]) return state.cache[letter];
  const res = await fetch(`data/index/index_${letter}.json`);
  if (!res.ok) return null;
  const data = await res.json();
  state.cache[letter] = data.tokens || {};
  return state.cache[letter];
}

function highlightText(text, query) {
  const normQ = normalizeToken(query);
  const re = /[A-Za-z����]+/g;
  let out = '';
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    const tok = m[0];
    const start = m.index;
    const end = start + tok.length;
    out += text.slice(last, start);
    out += normalizeToken(tok) === normQ ? `<mark>${tok}</mark>` : tok;
    last = end;
  }
  out += text.slice(last);
  return out;
}

function showStatus(msg) {
  const el = document.getElementById('status');
  if (el) el.textContent = msg || '';
}

function ensureResultsInterlinearToggle(){
  if (document.getElementById('btn-il-results-toggle')) return;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.id = 'btn-il-results-toggle';
  btn.textContent = state.searchInterlinearOn ? 'Mbylle Interlinear' : 'Shiko Interlinear';
  btn.addEventListener('click', () => {
    state.searchInterlinearOn = !state.searchInterlinearOn;
    btn.textContent = state.searchInterlinearOn ? 'Mbylle Interlinear' : 'Shiko Interlinear';
    if (state.lastRefs) renderResults(state.lastQuery || '', state.lastRefs);
  });
  // Place on its own line under the main controls, in its own il-row container
  const formEl = document.getElementById('search-form');
  let ilrow = document.getElementById('il-row');
  if (!ilrow && formEl){
    ilrow = document.createElement('div');
    ilrow.id = 'il-row';
    ilrow.className = 'il-row';
    formEl.appendChild(ilrow);
  }
  if (ilrow) ilrow.appendChild(btn); else {
    // Fallback: before results
    const res = document.getElementById('results');
    if (res) res.insertAdjacentElement('beforebegin', btn);
  }
}

function renderResults(q, refs) {
  // make sure toggle exists even if added late
  try { ensureResultsInterlinearToggle(); } catch(e){}
  const el = document.getElementById('results');
  if (!el) return;
  if (!refs || !refs.length) {
    el.innerHTML = '<p class="muted">Nuk ka rezultate.</p>';
    return;
  }
  const books = state.books || [];
  const verses = state.verses || [];
  const parts = [`<div class="muted">${refs.length} vargje</div>`];
  for (const vid of refs) {
    const row = verses[vid - 1];
    if (!row) continue;
    const [bid, chap, ver, text] = row;
    const bname = books[bid - 1] || `Libri ${bid}`;
    const inlineId = `il-inline-${vid}`;
    const slugById = BOOK_SLUGS_BY_ID[bid] || '';
    const ilBlock = state.searchInterlinearOn && slugById ? `<div class="il-inline" id="${inlineId}" data-slug="${slugById}" data-chap="${chap}" data-verse="${ver}"></div>` : '';
    const textHtml = state.searchInterlinearOn ? '' : ` - ${highlightText(sanitizeVerseText(text), q)}`;
    parts.push(`<div class="item"><span class="ref">${bname} ${chap}:${ver}</span>${textHtml}${ilBlock}</div>`);
  }
  el.innerHTML = parts.join('\n');
  state.lastRefs = refs.slice(0);
  state.lastQuery = q;
  if (state.searchInterlinearOn) {
    mountInterlinearForResults(refs);
  }
}

async function runSearch(q) {
  q = (q || '').trim();
  if (!q) return;
  showStatus('Po ngarkon indeksin...');
  const norm = normalizeToken(q);
  const letter = norm[0] || 'a';
  const shard = await loadIndexShard(letter);
  if (!shard) {
    showStatus('Indeksi nuk u gjet.');
    return;
  }
  const refs = shard[norm] || [];
  showStatus('Po ngarkon vargjet...');
  await Promise.all([loadBooks(), loadVerses()]);
  showStatus('');
  renderResults(q, refs);
}

function currentResultsHTML() {
  const container = document.getElementById('results');
  const title = (document.getElementById('q')?.value || '').trim();
  return (
    `<!doctype html><meta charset="utf-8">` +
    `<title>Rezultatet p�r ${title}</title>` +
    `<style>@media print{body{margin:.5in}} body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:1rem} .item{margin:.3rem 0; line-height:1.6} .ref{font-weight:600} mark{background:#fff3a3}</style>` +
    `<h1>Rezultatet p�r ${title}</h1>` +
    (container ? container.innerHTML : '')
  );
}

function downloadHTML(filename, html) {
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  URL.revokeObjectURL(url);
  a.remove();
}

function setupUI() {
  const form = document.getElementById('search-form');
  if (form) {
    // Ensure reference search controls exist (insert next to main search)
    if (!document.getElementById('refq')){
      try {
        const refRow = document.createElement('div');
        refRow.id = 'ref-row';
        refRow.className = 'ref-row';
        refRow.style.display = 'flex';
        refRow.style.gap = '.5rem';
        refRow.style.marginTop = '.5rem';
        refRow.style.flexBasis = '100%';
        refRow.style.width = '100%';

        const refInput = document.createElement('input');
        refInput.type = 'text';
        refInput.id = 'refq';
        refInput.placeholder = 'Gjej vargun (p.sh. Isaia 6:1)';
        refInput.autocomplete = 'off';
        refInput.style.maxWidth = '260px';
        const refBtn = document.createElement('button');
        refBtn.type = 'button';
        refBtn.id = 'btn-ref';
        refBtn.textContent = 'Gjej';
        refRow.appendChild(refInput);
        refRow.appendChild(refBtn);
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.insertAdjacentElement('afterend', refRow);
        else form.appendChild(refRow);
      } catch(e){}
    }
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const q = document.getElementById('q').value;
      runSearch(q);
    });
  }

  // Reference search: parse e.g., "Isaia 6:1" (Albanian names)
  const btnRef = document.getElementById('btn-ref');
  const refInput = document.getElementById('refq');
  if (btnRef && refInput){
    const doRefSearch = () => {
      const s = (refInput.value||'').trim();
      if (!s) return;
      findAndRenderReference(s);
    };
    btnRef.addEventListener('click', doRefSearch);
    refInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter'){ ev.preventDefault(); doRefSearch(); } });
  }

  // Add Interlinear toggle for search results
  try { ensureResultsInterlinearToggle(); } catch(e){}
  const btnPrint = document.getElementById('btn-print');
  if (btnPrint) btnPrint.addEventListener('click', () => window.print());
  const btnDl = document.getElementById('btn-download');
  if (btnDl)
    btnDl.addEventListener('click', () => {
      const q = document.getElementById('q').value || 'rezultate';
      downloadHTML(`kerkimi_${normalizeToken(q)}.html`, currentResultsHTML());
    });

  const home = document.getElementById('nav-home');
  const about = document.getElementById('nav-about');
  const browse = document.getElementById('nav-browse');
  if (home)
    home.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('search').style.display = '';
      document.getElementById('about').style.display = 'none';
      document.getElementById('browse').style.display = 'none';
    });
  if (about)
    about.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('search').style.display = 'none';
      document.getElementById('about').style.display = '';
      document.getElementById('browse').style.display = 'none';
    });
  if (browse)
    browse.addEventListener('click', async (e) => {
      e.preventDefault();
      document.getElementById('search').style.display = 'none';
      document.getElementById('about').style.display = 'none';
      const sec = document.getElementById('browse');
      sec.style.display = '';
      await showBooks();
    });
}
window.addEventListener('DOMContentLoaded', setupUI);

// ----- Browse: Books -> Chapters -> Verses -----
function buildChaptersByBook() {
  if (state.chaptersByBook) return state.chaptersByBook;
  const verses = state.verses || [];
  const map = {};
  for (const row of verses) {
    if (!row) continue;
    const bid = row[0], chap = row[1];
    if (!map[bid]) map[bid] = new Set();
    map[bid].add(chap);
  }
  const out = {};
  for (const k of Object.keys(map)) out[k] = Array.from(map[k]).sort((a, b) => a - b);
  state.chaptersByBook = out;
  return out;
}

async function showBooks() {
  await Promise.all([loadBooks(), loadVerses()]);
  const chaptersMap = buildChaptersByBook();
  const books = state.books || [];
  const container = document.getElementById('browse-books');
  const chaptersEl = document.getElementById('browse-chapters');
  const titleEl = document.getElementById('browse-title');
  const versesEl = document.getElementById('browse-verses');
  chaptersEl.style.display = 'none';
  titleEl.style.display = 'none';
  versesEl.innerHTML = '';
  const parts = [];
  for (let i = 0; i < books.length; i++) {
    const bid = i + 1;
    const name = books[i];
    parts.push(`<a href="#" data-bid="${bid}">${name}</a>`);
  }
  container.innerHTML = parts.join(' ');
  container.querySelectorAll('a[data-bid]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const bid = parseInt(e.currentTarget.getAttribute('data-bid'), 10);
      showChapters(bid);
    });
  });
}

function showChapters(bid) {
  const books = state.books || [];
  const chaptersMap = state.chaptersByBook || buildChaptersByBook();
  const chapters = chaptersMap[String(bid)] || [];
  const container = document.getElementById('browse-chapters');
  const titleEl = document.getElementById('browse-title');
  const versesEl = document.getElementById('browse-verses');
  titleEl.textContent = books[bid - 1] || `Libri ${bid}`;
  titleEl.style.display = '';
  versesEl.innerHTML = '';
  const parts = [`<a href="#" id="back-to-books">Shko mbrapa</a>`, ...chapters.map((c) => `<a href="#" data-chap="${c}">${c}</a>`)];
  container.innerHTML = parts.join(' ');
  container.style.display = '';
  const back = document.getElementById('back-to-books');
  if (back)
    back.addEventListener('click', (e) => {
      e.preventDefault();
      showBooks();
    });
  container.querySelectorAll('a[data-chap]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const chap = parseInt(e.currentTarget.getAttribute('data-chap'), 10);
      showChapterVerses(bid, chap);
    });
  });
}

function showChapterVerses(bid, chap) {
  const books = state.books || [];
  const verses = state.verses || [];
  const versesEl = document.getElementById('browse-verses');
  const items = [];
  for (let i = 0; i < verses.length; i++) {
    const row = verses[i];
    if (!row) continue;
    const [b, c, v, text] = row;
    if (b === bid && c === chap) {
      items.push(`<div class="item"><span class="ref">${books[bid - 1]} ${chap}:${v}</span> <button class="copy-btn copy-src" style="margin-left:.5rem" data-bid="${bid}" data-chap="${chap}" data-verse="${v}" title="Kopjo interlinear"><svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg></button> <button class="copy-btn copy-sq" style="margin-left:.35rem" title="Kopjo (Shqip)"><svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg></button> - <span class="sqtext">${cleanText(text)}</span></div>`);
    }
  }
  versesEl.innerHTML = items.length ? items.join('\n') : '<p class="muted">Nuk ka vargje.</p>';

  // Wire copy buttons to fetch interlinear and copy consonants/stripped text
  try {
    const buttons = versesEl.querySelectorAll('button.copy-btn[data-bid][data-chap][data-verse]');
    buttons.forEach(btn => {
      btn.addEventListener('click', async (ev) => {
        ev.preventDefault(); ev.stopPropagation();
        try {
          const bidVal = Number(btn.getAttribute('data-bid'))||0;
          const chapVal = Number(btn.getAttribute('data-chap'))||0;
          const vVal = Number(btn.getAttribute('data-verse'))||0;
          const slug = BOOK_SLUGS_BY_ID[bidVal] || '';
          if (!slug || !chapVal || !vVal) return;
          const path = `data/${slug}/${chapVal}.json`;
          const res = await fetch(path, { cache: 'no-store' });
          if (!res.ok) return;
          const data = await res.json();
          const isHeb = !!(data && data._meta && String(data._meta.lang_src||'').toLowerCase().startsWith('heb'));
          const verse = (data.verses||[]).find(x => Number(x && x.v) === vVal);
          if (!verse) return;
          const helper = (window.Interlinear && window.Interlinear.buildVerseText) ? window.Interlinear.buildVerseText : null;
          let text = '';
          if (helper) text = helper(verse, isHeb);
          else {
            // Fallback: build and normalize locally
            const words = Array.isArray(verse.src) ? verse.src.map(tok => (tok && tok.w) ? String(tok.w) : '').join(' ') : '';
            if (isHeb && window.Interlinear && window.Interlinear.hebrewConsonantsOnly) text = window.Interlinear.hebrewConsonantsOnly(words);
            else text = (words.normalize ? words.normalize('NFD').replace(/[\u0300-\u036f]/g,'') : words).replace(/\s+/g,' ').trim();
          }
          // Copy
          if (navigator && navigator.clipboard && navigator.clipboard.writeText){
            await navigator.clipboard.writeText(text);
          } else {
            const ta = document.createElement('textarea'); ta.value = text; ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta); ta.focus(); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
          }
          btn.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>';
          setTimeout(()=>{ btn.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'; }, 800);
        } catch(e) {}
      });
    });
    // Wire Albanian copy buttons (copy rendered sq text)
    const sqButtons = versesEl.querySelectorAll('button.copy-btn.copy-sq');
    sqButtons.forEach(btn => {
      btn.addEventListener('click', async (ev) => {
        ev.preventDefault(); ev.stopPropagation();
        try {
          const root = btn.closest('.item');
          const sqSpan = root ? root.querySelector('span.sqtext') : null;
          const text = sqSpan ? (sqSpan.textContent || '').trim() : '';
          if (!text) return;
          if (navigator && navigator.clipboard && navigator.clipboard.writeText){
            await navigator.clipboard.writeText(text);
          } else {
            const ta = document.createElement('textarea'); ta.value = text; ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta); ta.focus(); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
          }
          // success feedback
          btn.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>';
          btn.classList.add('copied');
          setTimeout(()=>{ btn.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'; btn.classList.remove('copied'); }, 900);
        } catch(e) {}
      });
    });
  } catch(e) {}
}

// Expose key functions for interop (e.g., assets/js/app.js)
window.showChapterVerses = showChapterVerses;
window.showChapters = showChapters;
window.showBooks = showBooks;




// Mapping by book id (1-based) used to load interlinear chapters for search results
const BOOK_SLUGS_BY_ID = [
  null,
  'genesis','exodus','leviticus','numbers','deuteronomy','joshua','judges','ruth',
  '1samuel','2samuel','1kings','2kings','1chronicles','2chronicles','ezra','nehemiah','esther','job',
  'psalms','proverbs','ecclesiastes','songofsongs','isaiah','jeremiah','lamentations','ezekiel','daniel',
  'hosea','joel','amos','obadiah','jonah','micah','nahum','habakkuk','zephaniah','haggai','zechariah','malachi',
  'matthew','mark','luke','john','acts','romans','1corinthians','2corinthians','galatians','ephesians','philippians','colossians',
  '1thessalonians','2thessalonians','1timothy','2timothy','titus','philemon','hebrews','james','1peter','2peter','1john','2john','3john','jude','revelation'
];

function mountInterlinearForResults(refs) {
  if (!Array.isArray(refs) || !refs.length) return;
  const verses = state.verses || [];
  for (const vid of refs) {
    const row = verses[vid - 1];
    if (!row) continue;
    const [bid, chap, ver] = row;
    const slug = BOOK_SLUGS_BY_ID[bid] || '';
    const mountEl = document.getElementById(`il-inline-${vid}`);
    if (!mountEl || !slug) continue;
    try {
      window.Interlinear.mountVerse({ book: slug, chapter: chap, verse: ver, mountId: mountEl.id, showRef: true });
    } catch (e) { /* ignore */ }
  }
}
// Normalize book titles for lookup (accent-insensitive, alpha+digits+spaces)
function normalizeBookTitle(s){
  s = String(s||'').toLowerCase();
  s = s.replace(/[?E]/g,'e').replace(/[??]/g,'c');
  s = s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g,'') : s;
  s = s.replace(/[^a-z0-9\s]/g,' ').replace(/\s+/g,' ').trim();
  return s;
}

function buildBookIndex(){
  const books = state.books || [];
  const idx = {};
  for (let i=0;i<books.length;i++){
    const name = books[i] || '';
    const key = normalizeBookTitle(name);
    if (key) idx[key] = i+1; // book id is 1-based
    // Add common contractions: remove connecting words like ' i ', ' e '
    const key2 = key.replace(/\b(i|e)\b/g,' ').replace(/\s+/g,' ').trim();
    if (key2 && !idx[key2]) idx[key2] = i+1;
  }
  return idx;
}

function parseRef(s){
  // Match: Book Name + space + chap[:verse]
  const m = s.match(/^\s*(.+?)\s+(\d+)(?::(\d+))?\s*$/);
  if (!m) return null;
  return { book: m[1], chap: Number(m[2]), verse: m[3] ? Number(m[3]) : null };
}

function findVerseId(bid, chap, verse){
  const verses = state.verses || [];
  for (let i=0;i<verses.length;i++){
    const r = verses[i];
    if (r && r[0]===bid && r[1]===chap && r[2]===verse){ return i+1; } // id is index+1
  }
  return null;
}

async function findAndRenderReference(input){
  await Promise.all([loadBooks(), loadVerses()]);
  const parsed = parseRef(input);
  if (!parsed){ showStatus('Formati: Libri Kapitulli:Vargu (p.sh., Isaia 6:1)'); return; }
  const idx = buildBookIndex();
  const bid = idx[normalizeBookTitle(parsed.book)] || null;
  if (!bid){ showStatus('Libri nuk u gjet. P�rdor emrin shqiptar nga lista e librave.'); return; }
  if (!parsed.verse){
    // No verse: show chapter in Browse block for context
    document.getElementById('search').scrollIntoView({behavior:'smooth'});
    showChapterVerses(bid, parsed.chap);
    return;
  }
  const vid = findVerseId(bid, parsed.chap, parsed.verse);
  if (!vid){ showStatus('Vargu nuk u gjet.'); return; }
  showStatus('');
  renderResults('', [vid]);
}


