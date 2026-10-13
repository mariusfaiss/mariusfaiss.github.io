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

  // ------------------------------------------------------------------ lightbox
  const box = document.getElementById("lightbox");
  const img = box.querySelector("img");
  const capLeft = box.querySelector(".lb-left");
  const capRight = box.querySelector(".lb-right");
  const count = box.querySelector(".lb-count");
  const prints = [...setsView.querySelectorAll(".prints .print")];
  const items = prints.map((fig) => {
    const set = fig.closest(".photo-set");
    const [left, right] = [...fig.querySelectorAll("figcaption span")].map((s) => s.textContent);
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
    capLeft.textContent = item.left || "";
    capRight.textContent = item.right || "";
    count.textContent = `${item.set} · ${item.index} / ${item.total}`;
    // Preload the neighbours so clicking through feels instant
    [current - 1, current + 1].forEach((j) => { new Image().src = items[(j + items.length) % items.length].large; });
  }

  function open(i) {
    box.hidden = false;
    document.documentElement.style.overflow = "hidden";
    show(i);
    box.querySelector(".lb-close").focus({ preventScroll: true });
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

  // Swipe on touch screens
  let touchX = null;
  box.addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; }, { passive: true });
  box.addEventListener("touchend", (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) show(current + (dx < 0 ? 1 : -1));
    touchX = null;
  });
})();
