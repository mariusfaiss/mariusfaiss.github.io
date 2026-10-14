// Photography page: stacks overview, set view with sticky titles, and a lightbox.
// The URL hash holds the open set (#masai-mara-hyenas), so the browser's back
// button and shared links work.
(() => {
  const overview = document.getElementById("overview");
  const setsView = document.getElementById("sets");
  if (!overview || !setsView) return;

  history.scrollRestoration = "manual";
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const stackTitle = (slug) => overview.querySelector(`.stack[data-set="${slug}"] .stack-title`);
  const barTitle = (slug) => document.querySelector(`#set-${slug} .back span`);
  const pageTop = (el) => el.getBoundingClientRect().top + scrollY;

  // Animate the set title from one place to the other where the browser supports it
  function morph(from, to, update) {
    if (!document.startViewTransition || reduceMotion || !from || !to) {
      update();
      return;
    }
    from.style.viewTransitionName = "set-title";
    const t = document.startViewTransition(() => {
      from.style.viewTransitionName = "";
      update();
      to.style.viewTransitionName = "set-title";
    });
    t.ready.catch(() => {}); // skipped transitions (e.g. hidden tab) are fine
    t.finished.finally(() => { to.style.viewTransitionName = ""; });
  }

  function openSet(slug, animate) {
    const section = document.getElementById(`set-${slug}`);
    if (!section) return showOverview(null, false);
    const update = () => {
      document.body.classList.add("viewing-set");
      overview.hidden = true;
      setsView.hidden = false;
      scrollTo(0, pageTop(section));
    };
    animate ? morph(stackTitle(slug), barTitle(slug), update) : update();
  }

  function showOverview(slug, animate) {
    const update = () => {
      document.body.classList.remove("viewing-set");
      setsView.hidden = true;
      overview.hidden = false;
      const stack = slug && overview.querySelector(`.stack[data-set="${slug}"]`);
      if (stack) stack.scrollIntoView({ block: "center" });
      else scrollTo(0, 0);
    };
    animate && slug ? morph(barTitle(slug), stackTitle(slug), update) : update();
  }

  function route() {
    const slug = decodeURIComponent(location.hash.slice(1));
    slug ? openSet(slug, false) : showOverview(null, false);
  }

  overview.addEventListener("click", (e) => {
    const stack = e.target.closest(".stack");
    if (!stack) return;
    e.preventDefault();
    history.pushState(null, "", `#${stack.dataset.set}`);
    openSet(stack.dataset.set, true);
  });

  setsView.addEventListener("click", (e) => {
    const back = e.target.closest(".back");
    if (!back) return;
    e.preventDefault();
    const slug = back.closest(".photo-set").dataset.set;
    history.pushState(null, "", location.pathname);
    showOverview(slug, true);
  });

  addEventListener("popstate", route);
  route();

  // ------------------------------------------------------- photo-book layout
  // Above phone width: put as many photos on a line as fit, all the same
  // height, filling the width exactly. Phones keep the simpler rows from CSS.
  const GAP = 34, PAD = 28;  // gap between prints, print border (left + right)
  function justify(box) {
    const prints = [...box.querySelectorAll(".print")];
    const W = box.clientWidth;
    if (!W) return;  // set not visible yet; the observer runs again when it is
    if (W < 600) {
      box.classList.remove("is-justified");
      prints.forEach((p) => { p.style.width = ""; });
      return;
    }
    box.classList.add("is-justified");
    const H = W > 800 ? 250 : 230;  // target photo height
    const ratio = prints.map((p) => parseFloat(p.style.getPropertyValue("--r")) || 1.5);
    const heightFor = (sum, n) => (W - GAP * (n - 1) - PAD * n) / sum;
    let line = [], sum = 0;
    const flush = (last) => {
      let h = heightFor(sum, line.length);
      if (last) h = Math.min(h, H);  // don't blow up a short last line
      line.forEach((i) => { prints[i].style.width = `${ratio[i] * h + PAD}px`; });
      line = []; sum = 0;
    };
    ratio.forEach((r, i) => {
      if (line.length && heightFor(sum + r, line.length + 1) < H) {
        // The next photo doesn't fit at full height: take it along (shrinking
        // the line) or start a new line, whichever stays closer to the target
        const withIt = heightFor(sum + r, line.length + 1);
        const without = heightFor(sum, line.length);
        if (Math.abs(Math.log(withIt / H)) < Math.abs(Math.log(without / H))) {  // compare as proportions
          line.push(i); sum += r; flush(false); return;
        }
        flush(false);
      }
      line.push(i); sum += r;
    });
    if (line.length) flush(true);
  }
  const observer = new ResizeObserver((entries) => entries.forEach((e) => justify(e.target)));
  setsView.querySelectorAll(".prints").forEach((box) => observer.observe(box));

  // ------------------------------------------------------------------ lightbox
  const box = document.getElementById("lightbox");
  const img = box.querySelector("img");
  const capLeft = box.querySelector(".lb-left");
  const capRight = box.querySelector(".lb-right");
  const count = box.querySelector(".lb-count");
  const prints = [...setsView.querySelectorAll(".prints .print")];
  const items = prints.map((fig) => {
    const set = fig.closest(".photo-set");
    const [left, right] = [...fig.querySelectorAll("figcaption > span")].map((s) => s.innerHTML);
    return {
      fig,
      large: fig.querySelector("a.frame").href,
      thumb: fig.querySelector("img").src,
      left, right,
      set: set.querySelector(".back span").textContent,
      index: [...set.querySelectorAll(".print")].indexOf(fig) + 1,
      total: set.querySelectorAll(".print").length,
    };
  });
  let current = -1;

  function show(i) {
    current = (i + items.length) % items.length;
    const item = items[current];
    // Show the thumbnail straight away, swap in the large image once loaded
    img.src = item.thumb;
    img.alt = item.fig.querySelector("img").alt;
    const large = new Image();
    large.onload = () => { if (items[current] === item) img.src = item.large; };
    large.src = item.large;
    capLeft.innerHTML = item.left || "";   // generated by tools/photos.py
    capRight.innerHTML = item.right || "";
    count.textContent = `${item.set} · ${item.index} / ${item.total}`;
    // Preload the neighbours so clicking through feels instant
    [current - 1, current + 1].forEach((j) => { new Image().src = items[(j + items.length) % items.length].large; });
  }

  function open(i) {
    box.hidden = false;
    document.documentElement.style.overflow = "hidden";
    show(i);
    box.focus({ preventScroll: true });  // for the keyboard, without a focus ring on the close button
  }

  function close() {
    box.hidden = true;
    document.documentElement.style.overflow = "";
    const fig = items[current] && items[current].fig;
    if (fig) fig.scrollIntoView({ block: "center" });
  }

  setsView.addEventListener("click", (e) => {
    const frame = e.target.closest(".prints a.frame");
    if (!frame) return;
    e.preventDefault();
    open(prints.indexOf(frame.closest(".print")));
  });

  box.querySelector(".lb-prev").addEventListener("click", () => show(current - 1));
  box.querySelector(".lb-next").addEventListener("click", () => show(current + 1));
  box.querySelector(".lb-close").addEventListener("click", close);
  box.addEventListener("click", (e) => {
    if (e.target === box || e.target.classList.contains("lb-stage")) close();
  });

  addEventListener("keydown", (e) => {
    if (box.hidden) return;
    if (e.key === "ArrowRight") show(current + 1);
    else if (e.key === "ArrowLeft") show(current - 1);
    else if (e.key === "Escape") close();
  });

  // Touch screens: swipe, or tap the photo on the left/right half of the screen
  let touchX = null, touchY = null;
  box.addEventListener("touchstart", (e) => {
    touchX = e.touches[0].clientX;
    touchY = e.touches[0].clientY;
  }, { passive: true });
  box.addEventListener("touchend", (e) => {
    if (touchX === null) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touchX, dy = t.clientY - touchY;
    touchX = null;
    if (Math.abs(dx) > 50) show(current + (dx < 0 ? 1 : -1));
    else if (Math.abs(dx) < 10 && Math.abs(dy) < 10 &&
             e.target.closest(".lb-print") && !e.target.closest("a")) {
      e.preventDefault();  // no click afterwards
      show(current + (t.clientX < innerWidth / 2 ? -1 : 1));
    }
  });
})();
