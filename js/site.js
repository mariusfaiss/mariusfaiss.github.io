// Shadow under the sticky name bar once the page is scrolled
(() => {
  const bar = document.querySelector(".masthead");
  if (!bar) return;
  const update = () => bar.classList.toggle("is-stuck", scrollY > 4);
  addEventListener("scroll", update, { passive: true });
  update();
})();
