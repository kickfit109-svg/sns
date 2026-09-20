// 小林凛太郎 プロキックボクシング教室 — 軽量スクリプト

// フッターの年号を自動更新
(function () {
  var el = document.getElementById("year");
  if (el) el.textContent = new Date().getFullYear();
})();

// スクロールで要素をフェードイン
(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var targets = document.querySelectorAll(
    ".record-card, .feature, .price-card, .schedule-card, .about-copy, .about-photo, .cta-box"
  );
  if (reduce || !("IntersectionObserver" in window)) {
    targets.forEach(function (t) { t.style.opacity = 1; });
    return;
  }
  targets.forEach(function (t) {
    t.style.opacity = 0;
    t.style.transform = "translateY(20px)";
    t.style.transition = "opacity .6s ease, transform .6s ease";
  });
  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.style.opacity = 1;
          e.target.style.transform = "none";
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  targets.forEach(function (t) { io.observe(t); });
})();
