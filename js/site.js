// Shadow under the sticky name bar once the page is scrolled
(() => {
  const bar = document.querySelector(".masthead");
  if (!bar) return;
  const update = () => bar.classList.toggle("is-stuck", scrollY > 4);
  addEventListener("scroll", update, { passive: true });
  update();
  // Its height, for the photo set bars that stick just below it
  new ResizeObserver(() => {
    document.documentElement.style.setProperty("--masthead-h", `${bar.offsetHeight}px`);
  }).observe(bar);
})();

// Looping videos: show only the still frame to visitors who prefer reduced motion
(() => {
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll("video[autoplay]").forEach((v) => {
    v.removeAttribute("autoplay");
    v.pause();
  });
})();

// About video: sits under the photos on wide screens, but between the text and
// the interest tags on phones; clicking it opens a larger view
(() => {
  const fig = document.querySelector(".print--video");
  if (!fig) return;
  const photos = document.querySelector(".about-prints");
  // On phones: above the last About paragraph (the one just before the tags)
  const spot = document.querySelector(".about-text .interests").previousElementSibling;
  const phone = matchMedia("(max-width: 640px)");
  const place = () => {
    if (phone.matches) spot.before(fig);
    else photos.append(fig);
    const v = fig.querySelector("video");
    if (v.autoplay) v.play().catch(() => {});  // moving an element pauses it
  };
  phone.addEventListener("change", place);
  place();

  fig.addEventListener("click", () => {
    const small = fig.querySelector("video");
    const viewer = document.createElement("div");
    viewer.className = "video-viewer";
    viewer.innerHTML = `<figure><video src="${small.currentSrc || small.src}" muted loop playsinline autoplay></video>
      <figcaption>${fig.querySelector("figcaption").textContent}</figcaption></figure>`;
    const big = viewer.querySelector("video");
    big.currentTime = small.currentTime;
    const close = () => { viewer.remove(); removeEventListener("keydown", onKey); document.documentElement.style.overflow = ""; };
    const onKey = (e) => { if (e.key === "Escape") close(); };
    viewer.addEventListener("click", close);
    addEventListener("keydown", onKey);
    document.documentElement.style.overflow = "hidden";
    document.body.append(viewer);
  });
})();
