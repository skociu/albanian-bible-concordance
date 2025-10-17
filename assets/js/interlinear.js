;(function(){
  function el(tag, attrs, children){
    const e = document.createElement(tag);
    if (attrs) for (const k in attrs){
      if (k === 'class') e.className = attrs[k];
      else if (k === 'style') e.style.cssText = attrs[k];
      else if (k.startsWith('on') && typeof attrs[k] === 'function') e.addEventListener(k.substring(2), attrs[k]);
      else e.setAttribute(k, attrs[k]);
    }
    if (children) for (const c of children){
      if (typeof c === 'string') e.appendChild(document.createTextNode(c));
      else if (c) e.appendChild(c);
    }
    return e;
  }

  const __ilChapterCache = new Map();

  async function fetchJSON(path){
    const res = await fetch(path, {cache:'no-store'});
    if (!res.ok) throw new Error('Failed to load ' + path);
    return res.json();
  }

  async function fetchChapter(path){
    if (__ilChapterCache.has(path)) return __ilChapterCache.get(path);
    const data = await fetchJSON(path);
    __ilChapterCache.set(path, data);
    return data;
  }

  function tokenTooltip(tok){
    const parts = [];
    if (tok.t) parts.push('Translit: ' + tok.t);
    if (tok.l) parts.push('Lemma: ' + tok.l);
    if (tok.m) parts.push('Morph: ' + tok.m);
    if (tok.s) parts.push('Strong: ' + tok.s);
    return parts.join(' \n');
  }

  function stripSlashes(s){ return String(s||'').split('/').join(''); }
  function greekDisplayWord(tok){ const w=String(tok.w||''); if(/[\u0370-\u03FF]/.test(w)) return stripSlashes(w); const t=String(tok.t||''); return t||stripSlashes(w); }

function cleanTxt(s){
    s = String(s||'');
    // Replace escaped quotes that may have leaked into data
    try {
      const BS = String.fromCharCode(92), DQ = '"', SQ = "'";
      s = s.split(BS + DQ).join(DQ).split(BS + SQ).join(SQ);
      // Strip spurious debug markers found in some source lines (e.g., "aaa see ..." or "aaa eee ...")
      s = s.replace(/^\s*aaa\s+(see|eee)\s*I?\s+/i, '');
      // Collapse excessive whitespace
      s = s.replace(/\s+/g, ' ').trim();
    } catch (e) {}
    return s;
  }

  // Clipboard helper with fallback
  async function copyTextToClipboard(text){
    try {
      if (navigator && navigator.clipboard && navigator.clipboard.writeText){
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch(e) {}
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return !!ok;
    } catch(e) { return false; }
  }

  // Build full-verse text from tokens
  function hebrewConsonantsOnly(s){
    s = String(s||'');
    try {
      // Remove Hebrew diacritics (niqqud + cantillation) and punctuation marks
      s = s.replace(/[\u0591-\u05C7]/g, '');
      // Hebrew punctuation/marks frequently present
      s = s.replace(/[\u05BE\u05C0\u05C3\u05F3\u05F4]/g, '');
      // Remove bidi/formatting controls just in case
      s = s.replace(/[\u200E\u200F\u202A-\u202E]/g, '');
    } catch(e) {}
    // Collapse whitespace
    s = s.replace(/\s+/g,' ').trim();
    return s;
  }

  function greekRemoveDiacritics(s){
    s = String(s||'');
    try {
      // Decompose to base + combining, then drop combining marks
      s = s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g,'') : s;
      // Remove bidirectional/formatting controls
      s = s.replace(/[\u200E\u200F\u202A-\u202E]/g, '');
    } catch(e) {}
    return s.replace(/\s+/g,' ').trim();
  }

  // Upgrade simple text/emoji buttons to SVG icon buttons
  function svgClipboardIcon(){
    try {
      const ns='http://www.w3.org/2000/svg';
      const s=document.createElementNS(ns,'svg'); s.setAttribute('class','copy-ic'); s.setAttribute('width','16'); s.setAttribute('height','16'); s.setAttribute('viewBox','0 0 24 24'); s.setAttribute('aria-hidden','true'); s.setAttribute('focusable','false');
      const p=document.createElementNS(ns,'path'); p.setAttribute('fill','currentColor');
      p.setAttribute('d','M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z');
      s.appendChild(p); return s;
    } catch(e) { return null; }
  }

  function upgradeCopyButtons(root){
    try {
      const scope = root || document;
      const btns = scope.querySelectorAll('button.copy-btn');
      btns.forEach(btn => {
        if (!btn.querySelector('svg.copy-ic')){
          try { while (btn.firstChild) btn.removeChild(btn.firstChild); } catch(e){}
          const ic = svgClipboardIcon(); if (ic) btn.appendChild(ic);
        }
        if (!btn.style.marginLeft) btn.style.marginLeft = '.5rem';
      });
    } catch(e){}
  }

  function buildVerseText(verse, isHeb){
    try {
      if (!verse || !Array.isArray(verse.src)) return '';
      if (isHeb){
        const joined = verse.src.map(tok => stripSlashes(tok && tok.w || '')).join(' ');
        return hebrewConsonantsOnly(joined);
      } else {
        const joined = verse.src.map(tok => greekDisplayWord(tok)).join(' ');
        return greekRemoveDiacritics(joined);
      }
    } catch(e) { return ''; }
  }

  function textFromNode(root){
    if (!root) return '';
    try {
      const isHeb = !!(root.querySelector('.il-row.il-row-a[dir="rtl"]') || root.querySelector('.il-heb'));
      const words = Array.from(root.querySelectorAll('.il-row.il-row-a .mid-word'))
        .map(n => (n && n.textContent) ? n.textContent : '')
        .filter(Boolean);
      const joined = words.join(' ').replace(/\s+/g,' ').trim();
      return isHeb ? hebrewConsonantsOnly(joined) : greekRemoveDiacritics(joined);
    } catch(e) { return ''; }
  }

  function renderVerse(container, verse, isHeb, refLabel){
    const wrap = el('div', {class:'il-verse', role:'rowgroup'});
    // Reference label (matches browse display style)
    if (refLabel){
      const ref = el('div', {class:'il-ref', role:'rowheader'});
      const refSpan = el('span', {class:'ref'}, [refLabel]);
      const btn = el('button', { class:'copy-btn copy-src', type:'button', style:'margin-left:.5rem', title: isHeb ? 'Kopjo (Heb. bashkëting.)' : 'Kopjo (Greqisht)' }, [
        el('span', {class:'copy-ic', 'aria-hidden':'true'}, ['📋'])
      ]);
      btn.addEventListener('click', async (ev) => {
        ev.preventDefault(); ev.stopPropagation();
        try {
          const text = buildVerseText(verse, isHeb);
          const ok = await copyTextToClipboard(text);
          if (ok){
  btn.classList.add('copied');
  try {
    // swap to check
    btn.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>';
    setTimeout(()=>{ btn.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'; btn.classList.remove('copied'); }, 900);
  } catch(e){}
}
        } catch(e){}
      });
      ref.appendChild(refSpan);
      ref.appendChild(btn);
      // Secondary copy button: Albanian (Shqip)
      const btnSq = el('button', { class:'copy-btn copy-sq', type:'button', style:'margin-left:.35rem', title:'Kopjo (Shqip)' });
      btnSq.addEventListener('click', async (ev) => {
        ev.preventDefault(); ev.stopPropagation();
        try {
          const text = cleanTxt(verse && verse.sq ? verse.sq : '');
          if (!text) return;
          const ok = await copyTextToClipboard(text);
          if (ok){
            btnSq.classList.add('copied');
            try {
              btnSq.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>';
              setTimeout(()=>{ btnSq.innerHTML = '<svg class="copy-ic" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'; btnSq.classList.remove('copied'); }, 900);
            } catch(e){}
          }
        } catch(e){}
      });
      ref.appendChild(btnSq);
      wrap.appendChild(ref);
    }
    const rowA = el('div', {class:'il-row il-row-a', role:'row'});
    if (isHeb) rowA.setAttribute('dir','rtl');
    const rowB = el('div', {class:'il-row il-row-b', role:'row'});
    const rowC = el('div', {class:'il-row il-row-c', role:'row'});
    // Row A: tokens
    let sqTokens = [];
    const alignedMap = {};
    let stackedGreek = false;
    try {
      if (verse && verse.sq) sqTokens = String(verse.sq).split(/\s+/);
      const at = verse && verse.align_tok ? verse.align_tok : [];
      if (Array.isArray(at)){
        for (const m of at){
          if (m && typeof m.src === 'number' && Array.isArray(m.tgt) && m.tgt.length){
            const lo = m.tgt[0]|0; const hi = (m.tgt[1] != null ? m.tgt[1] : lo)|0;
            alignedMap[m.src] = sqTokens.slice(Math.max(0,lo), Math.min(sqTokens.length, hi+1)).join(' ');
          }
        }
      }
    } catch(e) {}

    if (isHeb) {
      const usedAligned = new Set();
      for (let _i = 0; _i < verse.src.length; _i++) {
        const tok = verse.src[_i];
        const cell = el('span', {class:'il-cell token il-token-col il-heb', tabindex:'0', title: tokenTooltip(tok), role:'cell'});
        const s = (tok.s||'').startsWith('H') ? tok.s : '';
        const top1 = el('div', {class:'top-strong'}, [s]);
        const mid = el('div', {class:'mid-word'}, [stripSlashes(tok.w)]);
        try {
          if (typeof tok.i === 'number'){
            const partsCount = Math.max(1, String(tok.l||'').split('/').length);
            for (let k=0; k<partsCount; k++){
              const idx = tok.i + k;
              if (!usedAligned.has(idx) && Object.prototype.hasOwnProperty.call(alignedMap, idx)){
                usedAligned.add(idx);
              }
            }
          }
        } catch(e) {}
        cell.appendChild(top1);
        cell.appendChild(mid);
        rowA.appendChild(cell);
      }
    } else {
      for (const tok of verse.src){
        const hasStrong = tok.s && tok.s.startsWith('G');
        const useStack = hasStrong;
        if (useStack){
          stackedGreek = true;
          const cell = el('span', {class:'il-cell token il-token-col il-gr', tabindex:'0', title: tokenTooltip(tok), role:'cell'});
          const s = hasStrong ? tok.s : '';
          const top1 = el('div', {class:'top-strong'}, [s]);
          const mid = el('div', {class:'mid-word'}, [stripSlashes(tok.w)]);
          cell.appendChild(top1);
          cell.appendChild(mid);
          rowA.appendChild(cell);
        } else {
          const cell = el('span', {class:'il-cell token', tabindex:'0', title: tokenTooltip(tok), role:'cell'});
          cell.textContent = greekDisplayWord(tok);
          rowA.appendChild(cell);
        }
      }
    }
    if (!isHeb && !stackedGreek){
      for (const tok of verse.src){
        const meta = [tok.l, tok.m, tok.s].filter(Boolean).join(' | ');
        const cell = el('span', {class:'il-cell meta', role:'cell'}, [meta]);
        rowB.appendChild(cell);
      }
    }
    rowC.appendChild(el('div', {class:'il-cell sq', role:'cell'}, [cleanTxt(verse.sq)]));
    wrap.appendChild(rowA); wrap.appendChild(rowB); wrap.appendChild(rowC);
    container.appendChild(wrap);
  }

  async function mount(opts){
    const root = document.getElementById(opts.mountId);
    if (!root) throw new Error('Mount root not found');
    root.innerHTML = '';
    const path = `data/${opts.book.toLowerCase()}/${opts.chapter}.json`;
    const data = await fetchChapter(path);
    root.setAttribute('role','table');
    root.setAttribute('aria-label', `${data.ref.book_sq} ${data.ref.chapter} interlinear`);
    const isHeb = !!(data._meta && data._meta.lang_src && String(data._meta.lang_src).toLowerCase().startsWith('heb'));
    if (isHeb) root.setAttribute('dir','rtl'); else root.removeAttribute('dir');
    for (const v of data.verses){
      const refLabel = `${data.ref.book_sq} ${data.ref.chapter}:${v.v}`;
      renderVerse(root, v, isHeb, refLabel);
    }
    try { upgradeCopyButtons(root); } catch(e){}
  }

  async function mountVerse(opts){
    const root = document.getElementById(opts.mountId);
    if (!root) throw new Error('Mount root not found');
    root.innerHTML = '';
    const path = `data/${opts.book.toLowerCase()}/${opts.chapter}.json`;
    const data = await fetchChapter(path);
    root.setAttribute('role','table');
    root.setAttribute('aria-label', `${data.ref.book_sq} ${data.ref.chapter}:${opts.verse} interlinear`);
    const isHeb = !!(data._meta && data._meta.lang_src && String(data._meta.lang_src).toLowerCase().startsWith('heb'));
    if (isHeb) root.setAttribute('dir','rtl'); else root.removeAttribute('dir');
    const vv = Number(opts.verse)||0;
    const hit = (data.verses||[]).find(x => Number(x.v) === vv);
    if (hit){
      const showRef = !!opts.showRef; // default false for search inline
      const refLabel = showRef ? `${data.ref.book_sq} ${data.ref.chapter}:${hit.v}` : null;
      renderVerse(root, hit, isHeb, refLabel);
    }
    try { upgradeCopyButtons(root); } catch(e){}
  }

  window.Interlinear = { mount, mountVerse, textFromNode, buildVerseText, hebrewConsonantsOnly };
})();







