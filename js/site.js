// Shadow under the sticky name bar once the page is scrolled
(() => {
  const bar = document.querySelector(".masthead");
  if (!bar) return;
  const update = () => bar.classList.toggle("is-stuck", scrollY > 4);
  addEventListener("scroll", update, { passive: true });
  update();
})();

// Looping videos: show only the still frame to visitors who prefer reduced motion
(() => {
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll("video[autoplay]").forEach((v) => {
    v.removeAttribute("autoplay");
    v.pause();
  });
})();
