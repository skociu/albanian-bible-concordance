// Enhancements layered on top of existing site/app.js
;(function(){
  // Accent-insensitive normalization helper
  function normalizeKey(s){
    let k = String(s||'').trim().toLowerCase();
    try { k = k.normalize('NFD').replace(/[\u0300-\u036f]/g,''); } catch(e) {}
    k = k.replace(/[^a-z0-9\s]/g,' ').replace(/\s+/g,' ').trim();
    return k;
  }

  // Static mapping by book id (1-based, follows site/data/books.json order)
  const BOOK_SLUGS_BY_ID = [
    null,
    'genesis','exodus','leviticus','numbers','deuteronomy','joshua','judges','ruth',
    '1samuel','2samuel','1kings','2kings','1chronicles','2chronicles','ezra','nehemiah','esther','job',
    'psalms','proverbs','ecclesiastes','songofsongs','isaiah','jeremiah','lamentations','ezekiel','daniel',
    'hosea','joel','amos','obadiah','jonah','micah','nahum','habakkuk','zephaniah','haggai','zechariah','malachi',
    'matthew','mark','luke','john','acts','romans','1corinthians','2corinthians','galatians','ephesians','philippians','colossians',
    '1thessalonians','2thessalonians','1timothy','2timothy','titus','philemon','hebrews','james','1peter','2peter','1john','2john','3john','jude','revelation'
  ];

  // Minimal name fallback (resilient to diacritics)
  const NORM_BOOK_SLUGS = {
    'zanafilla':'genesis','eksodi':'exodus','levitiku':'leviticus','numrat':'numbers','ligji i perterire':'deuteronomy',
    'jozueu':'joshua','gjyqtaret':'judges','ruthi':'ruth','isaia':'isaiah','jeremia':'jeremiah','vajtimet':'lamentations',
    'ezekieli':'ezekiel','danieli':'daniel','psalmet':'psalms','fjalet e urta':'proverbs','predikuesi':'ecclesiastes','kenga e kengeve':'songofsongs',
    'mateu':'matthew','marku':'mark','luka':'luke','gjoni':'john','veprat e apostujve':'acts','romakeve':'romans'
  };

  function currentSlugAndChap(bname, chap, bid){
    const c = Number(chap)||1;
    let slug = '';
    if (typeof bid === 'number' && bid >= 1 && bid < BOOK_SLUGS_BY_ID.length){
      slug = BOOK_SLUGS_BY_ID[bid] || '';
    }
    if (!slug){
      const rawKey = String(bname||'').trim().toLowerCase();
      const normKey = normalizeKey(rawKey);
      slug = NORM_BOOK_SLUGS[normKey] || '';
    }
    return { slug, chap: c };
  }

  function ensureToggle(bname, chap, bid){
    try {
      const titleEl = document.getElementById('browse-title');
      const versesEl = document.getElementById('browse-verses');
      if (!titleEl || !versesEl) return;
      const name = bname || (titleEl.textContent || '');
      const { slug, chap: c } = currentSlugAndChap(name, chap, bid);
      const eligible = !!slug && c >= 1;
      let wrap = document.getElementById('interlinear-toggle-wrap');
      if (!eligible){ if (wrap) wrap.remove(); return; }
      if (!wrap){
        wrap = document.createElement('div');
        wrap.id = 'interlinear-toggle-wrap';
        const btn = document.createElement('button');
        btn.id = 'btn-il-toggle';
        btn.className = 'il-toggle';
        btn.textContent = (window.InterlinearState && window.InterlinearState.on) ? 'Mbylle Interlinear' : 'Shiko Interlinear';
        btn.setAttribute('aria-controls', 'interlinear-root');
        const root = document.createElement('div');
        root.id = 'interlinear-root';
        titleEl.insertAdjacentElement('afterend', wrap);
        wrap.appendChild(btn);
        wrap.appendChild(root);
        btn.addEventListener('click', async () => {
          const on = !(window.InterlinearState && window.InterlinearState.on);
          const ds = wrap.dataset;
          window.InterlinearState = { on, slug: ds.slug||slug, chap: Number(ds.chap||c)||1 };
          btn.textContent = on ? 'Mbylle Interlinear' : 'Shiko Interlinear';
          // Hide/show the regular verses below while interlinear is active
          if (versesEl) versesEl.style.display = on ? 'none' : '';
          if (on){
            await window.Interlinear.mount({ book: window.InterlinearState.slug, chapter: window.InterlinearState.chap, mountId: 'interlinear-root' });
            root.scrollIntoView({behavior:'smooth', block:'start'});
          } else {
            root.innerHTML = '';
            // Restore verses content explicitly to avoid empty state
            try {
              const bidVal = Number(ds.bid||0)||0;
              const chapVal = Number(ds.chap||c)||1;
              if (versesEl) versesEl.style.display = '';
              if (bidVal && typeof window.showChapterVerses === 'function'){
                window.showChapterVerses(bidVal, chapVal);
              }
            } catch(e){}
          }
        });
      }
      // update dataset on each call
      wrap.dataset.slug = slug;
      wrap.dataset.chap = String(c);
      if (typeof bid === 'number') wrap.dataset.bid = String(bid);
      // auto-enable from hash or prior state
      try {
        const qp = new URLSearchParams(location.hash.split('?')[1]||'');
        const wantOn = ['on','1','true','interlinear'].includes((qp.get('mode')||'').toLowerCase());
        if (!window.InterlinearState && wantOn){
          window.InterlinearState = { on:true, slug, chap:c };
          const btn = document.getElementById('btn-il-toggle');
          if (btn) btn.click();
        }
      } catch(e){}
      const root = document.getElementById('interlinear-root');
      if (window.InterlinearState && window.InterlinearState.on){
        const prev = window.InterlinearState;
        if (prev.slug !== slug || prev.chap !== c){
          window.InterlinearState = { on:true, slug, chap: c };
          window.Interlinear.mount({ book: slug, chapter: c, mountId: 'interlinear-root' });
        }
        if (versesEl) versesEl.style.display = 'none';
      } else {
        if (versesEl) versesEl.style.display = '';
      }
    } catch (e) { console.warn('Interlinear toggle error', e); }
  }

  // Hook into showChapterVerses to keep toggle in sync
  const MAX_WAIT = 3000;
  function waitForShowChapterVerses(){
    const start = Date.now();
    const iv = setInterval(() => {
      if (typeof window.showChapterVerses === 'function'){
        clearInterval(iv);
        const orig = window.showChapterVerses;
        window.showChapterVerses = function(bid, chap){
          orig.apply(this, arguments);
          const titleEl = document.getElementById('browse-title');
          const name = titleEl ? (titleEl.textContent || '') : '';
          ensureToggle(name, chap, bid);
        };
      } else if (Date.now() - start > MAX_WAIT){
        clearInterval(iv);
      }
    }, 100);
  }

  window.addEventListener('DOMContentLoaded', () => {
    const footerSpan = document.querySelector('footer .muted');
    if (footerSpan){
      // Keep footer text authoritative; no extra note needed
      // If older text is present, normalize it to the latest wording
      const want = 'Tekst në domenin publik (ALB – Scrollmapper). Ndërtuar për edukim dhe studim. Interlinear: TR 1894 (Domen publik), WLC (OSHB, CC BY 4.0), TBESG (CC BY 4.0).';
      try {
        const t = footerSpan.textContent || '';
        if (!t.includes('ALB') || !t.includes('Interlinear')) footerSpan.textContent = want;
      } catch(e){ footerSpan.textContent = want; }
      // Remove any legacy appended interlinear spans right after the footer text
      try {
        let el = footerSpan.nextElementSibling;
        while (el && el.classList && el.classList.contains('muted') && /Interlinear/i.test(el.textContent||'')){
          const next = el.nextElementSibling;
          el.remove();
          el = next;
        }
      } catch(e){}
    }
    waitForShowChapterVerses();
  });
})();

