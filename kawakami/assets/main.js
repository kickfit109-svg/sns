// 川上かずき 公式サイト
// 全画面メニュー／スクロール進捗リングと細いバー／スクロール表示／視差／数字のカウントアップ
// ※ JavaScript が無くても全文が読めます（動きの待機状態は .js / .reveal-ready が付いた時だけ）
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.add('js', 'reveal-ready');

  // ---- ヒーローの登場（Webフォントを最大0.8秒待ってから再生） ----
  var started = false;
  var start = function () {
    if (started) return;
    started = true;
    requestAnimationFrame(function () { root.classList.add('loaded'); });
  };
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(start);
    setTimeout(start, 800);
  } else {
    start();
  }

  // ---- 丸いメニューボタンと全画面メニュー ----
  var btn = document.querySelector('.menu-btn');
  var menu = document.getElementById('site-menu');
  if (btn && menu) {
    var label = btn.querySelector('.menu-label');
    var setOpen = function (open) {
      btn.setAttribute('aria-expanded', String(open));
      btn.setAttribute('aria-label', open ? 'メニューを閉じる' : 'メニューを開く');
      if (label) label.textContent = open ? '閉じる' : 'メニュー';
      menu.classList.toggle('is-open', open);
      menu.setAttribute('aria-hidden', String(!open));
      root.classList.toggle('menu-open', open);
      if (open) {
        var first = menu.querySelector('a');
        if (first) setTimeout(function () { first.focus({ preventScroll: true }); }, 120);
      }
    };
    btn.addEventListener('click', function () {
      setOpen(btn.getAttribute('aria-expanded') !== 'true');
    });
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') { setOpen(false); btn.focus(); }
    });
  }

  // ---- SNS：URL未設定（href="#"）のアイコンは押しても何もしない ----
  document.querySelectorAll('.sns a[href="#"]').forEach(function (a) {
    a.removeAttribute('target');
    a.setAttribute('aria-disabled', 'true');
    a.addEventListener('click', function (e) { e.preventDefault(); });
  });

  // ---- 順番に表示（data-stagger の中の .reveal に遅延を付ける） ----
  document.querySelectorAll('[data-stagger]').forEach(function (group) {
    group.querySelectorAll('.reveal').forEach(function (el, i) {
      el.style.setProperty('--i', i % 4);
    });
  });

  // ---- 数字のカウントアップ ----
  var countUp = function (el) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (isNaN(target) || reduce) return;
    var t0 = null;
    var dur = 1400;
    var step = function (t) {
      if (!t0) t0 = t;
      var p = Math.min((t - t0) / dur, 1);
      el.textContent = String(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  // ---- スクロールで表示 ----
  var targets = document.querySelectorAll('.reveal, .reveal-wipe, [data-count]');
  if (!('IntersectionObserver' in window)) {
    targets.forEach(function (el) { el.classList.add('is-in'); });
  } else {
    // clip-path で隠している要素は Chrome では「見えていない」扱いになるため、親要素を監視する
    var watched = [];
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var i = watched.indexOf(entry.target);
        var el = i > -1 ? targets[i] : entry.target;
        el.classList.add('is-in');
        if (el.hasAttribute('data-count')) countUp(el);
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.08 });
    targets.forEach(function (el) {
      var w = el.classList.contains('reveal-wipe') ? el.parentElement : el;
      watched.push(w);
      io.observe(w);
    });
  }

  // ---- スクロール連動：ヘッダー・進捗バー・トップへ戻る・視差 ----
  var toTop = document.querySelector('.to-top');
  var header = document.querySelector('.site-header');
  var miniBar = document.querySelector('.mini-bar');
  var parallax = reduce ? [] : Array.prototype.slice.call(document.querySelectorAll('[data-parallax]'));
  // メインビジュアルの奥行き（人物・コピー・山並みをスクロール量に応じて別々の速さで動かす）
  var depth = reduce ? [] : Array.prototype.slice.call(document.querySelectorAll('[data-depth]'));
  var ticking = false;
  var update = function () {
    var y = window.pageYOffset || document.documentElement.scrollTop;
    var max = document.documentElement.scrollHeight - window.innerHeight;
    root.style.setProperty('--progress', max > 0 ? Math.min(y / max, 1).toFixed(4) : '0');
    if (miniBar && header) miniBar.classList.toggle('is-visible', y > header.offsetHeight + 40);
    if (toTop) toTop.classList.toggle('is-visible', y > 700);
    var vh = window.innerHeight;
    if (y < vh * 1.4) {
      depth.forEach(function (el) {
        var d = parseFloat(el.getAttribute('data-depth')) || 0;
        el.style.translate = '0 ' + (y * d).toFixed(1) + 'px';
      });
    }
    parallax.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.bottom < -100 || r.top > vh + 100) return;
      var speed = parseFloat(el.getAttribute('data-parallax')) || 0.08;
      var offset = (r.top + r.height / 2 - vh / 2) * -speed;
      el.style.setProperty('--py', offset.toFixed(1) + 'px');
    });
    ticking = false;
  };
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  window.addEventListener('resize', update);
  update();
})();
