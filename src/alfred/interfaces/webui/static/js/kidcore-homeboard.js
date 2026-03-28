const ACTIVE_HOMEBOARD_THEMES = new Set(["kidcore-playground", "spacejam-neocities"]);
const HOMEBOARD_STORAGE_KEY = "alfred-kidcore-homeboard";
const GUESTBOOK_STORAGE_KEY = "alfred-kidcore-guestbook";

const DEFAULT_HOMEBOARD_STATE = Object.freeze({
  activeTab: "guestbook",
  webringIndex: 0,
  linkIndex: 0,
  windowState: "open",
  windowLeft: 16,
  windowTop: 100,
});

const DEFAULT_GUESTBOOK_ENTRIES = Object.freeze([
  {
    name: "Mossy Star",
    message: "your little homepage feels like finding a sticker in a library book",
    createdAt: "2026-03-01T10:15:00.000Z",
  },
  {
    name: "Rain Tape",
    message: "please keep making pages that look like somebody stayed up too late with glitter",
    createdAt: "2026-03-07T18:40:00.000Z",
  },
  {
    name: "Tiny Comet",
    message: "guestbooks are proof the web can still be kind",
    createdAt: "2026-03-12T21:05:00.000Z",
  },
]);

const WEBRING_SITES = Object.freeze([
  {
    title: "Kidcore Wonderland",
    url: "raining-starss.neocities.org",
    description: "a scrapbook of nostalgia pages, toy lists, and bright little obsessions",
    note: "buttons, journals, and very sincere enthusiasm",
  },
  {
    title: "Z.T.T.P.W.",
    url: "zeronic.neocities.org",
    description: "unfinished on purpose, full of buttons, jokes, and personal corners",
    note: "the layout says “home page,” the voice says “come in, friend”",
  },
  {
    title: "Fishmael’s Pond",
    url: "fishmaels-pond.neocities.org",
    description: "soft, friendly, and a little pond-like — stories, notes, and tiny projects",
    note: "the kind of site that remembers to wave back",
  },
  {
    title: "Retro Haven",
    url: "retro-haven.neocities.org",
    description: "a busy little archive with links, shrines, and an obvious love for the web",
    note: "guestbook energy, update-log energy, “i made this myself” energy",
  },
  {
    title: "55-Pedro",
    url: "55-pedro.neocities.org",
    description: "big banners, buttons, and a homepage that feels like a desk covered in postcards",
    note: "chaotic, warm, and fully committed to the bit",
  },
]);

const LINK_CARDS = Object.freeze([
  {
    label: "guestbook",
    title: "guestbook",
    description: "leave a small note so the page remembers you were here",
    url: "alfred.local/guestbook",
    note: "best for doodles, hello messages, and tiny compliments",
  },
  {
    label: "buttons",
    title: "button wall",
    description: "a stash of tiny badges, blinkies, and site buttons",
    url: "alfred.local/buttons",
    note: "little images, big personality",
  },
  {
    label: "webring",
    title: "webring",
    description: "a pretend little loop of adjacent homes on the web",
    url: "alfred.local/webring",
    note: "prev / random / next, like a tiny neighborhood map",
  },
  {
    label: "friends",
    title: "friends",
    description: "fake postcards from imaginary pals and their little pages",
    url: "alfred.local/friends",
    note: "warm, messy, and proudly handmade",
  },
  {
    label: "updates",
    title: "update log",
    description: "a tiny notebook for page changes, experiments, and new doodles",
    url: "alfred.local/updates",
    note: "the best part of an old personal site",
  },
]);

function isKidcoreThemeActive() {
  return ACTIVE_HOMEBOARD_THEMES.has(document.documentElement.getAttribute("data-theme") || "");
}

function readJSON(storageKey, fallback) {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) {
      return fallback;
    }

    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function writeJSON(storageKey, value) {
  localStorage.setItem(storageKey, JSON.stringify(value));
}

function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function createElement(tagName, className, textContent = "") {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  if (textContent) {
    element.textContent = textContent;
  }
  return element;
}

class KidcoreHomeboard {
  constructor(root) {
    this.root = root;
    this.window = document.getElementById("kidcore-homeboard-window");
    this.windowBody = document.getElementById("kidcore-homeboard-body");
    this.launcherButton = document.getElementById("kidcore-homeboard-launcher");
    this.titlebar = document.getElementById("kidcore-homeboard-titlebar");
    this.collapseButton = document.getElementById("kidcore-homeboard-collapse");
    this.closeButton = document.getElementById("kidcore-homeboard-close");
    this.dragState = null;
    this.isCompactViewport = window.matchMedia("(max-width: 720px)");

    const storedState = readJSON(HOMEBOARD_STORAGE_KEY, {});
    const persistedState =
      storedState && typeof storedState === "object" && !Array.isArray(storedState)
        ? storedState
        : {};
    this.state = {
      ...DEFAULT_HOMEBOARD_STATE,
      ...persistedState,
    };

    if (
      typeof persistedState.windowState !== "string" ||
      !["open", "collapsed", "closed"].includes(persistedState.windowState)
    ) {
      this.state.windowState = this.isCompactViewport.matches ? "collapsed" : "open";
    }
    if (typeof this.state.windowLeft !== "number" || !Number.isFinite(this.state.windowLeft)) {
      this.state.windowLeft = DEFAULT_HOMEBOARD_STATE.windowLeft;
    }
    if (typeof this.state.windowTop !== "number" || !Number.isFinite(this.state.windowTop)) {
      this.state.windowTop = DEFAULT_HOMEBOARD_STATE.windowTop;
    }

    const storedGuestbookEntries = readJSON(GUESTBOOK_STORAGE_KEY, []);
    this.userGuestbookEntries = Array.isArray(storedGuestbookEntries) ? storedGuestbookEntries : [];

    this.tabButtons = Array.from(this.root.querySelectorAll("[data-kidcore-tab]"));
    this.panels = {
      guestbook: this.root.querySelector("#kidcore-guestbook-panel"),
      webring: this.root.querySelector("#kidcore-webring-panel"),
      links: this.root.querySelector("#kidcore-links-panel"),
      updates: this.root.querySelector("#kidcore-updates-panel"),
    };

    this.guestbookForm = this.root.querySelector("#kidcore-guestbook-form");
    this.guestbookNameInput = this.root.querySelector("#kidcore-guestbook-name");
    this.guestbookMessageInput = this.root.querySelector("#kidcore-guestbook-message");
    this.guestbookEntriesList = this.root.querySelector("#kidcore-guestbook-entries");

    this.webringPrevButton = this.root.querySelector("#kidcore-webring-prev");
    this.webringRandomButton = this.root.querySelector("#kidcore-webring-random");
    this.webringNextButton = this.root.querySelector("#kidcore-webring-next");
    this.webringVisitButton = this.root.querySelector("#kidcore-webring-visit");
    this.webringPosition = this.root.querySelector("#kidcore-webring-position");
    this.webringTitle = this.root.querySelector("#kidcore-webring-title");
    this.webringDescription = this.root.querySelector("#kidcore-webring-description");
    this.webringUrl = this.root.querySelector("#kidcore-webring-url");
    this.webringNote = this.root.querySelector("#kidcore-webring-note");

    this.linkButtons = Array.from(this.root.querySelectorAll("[data-kidcore-link]"));
    this.linkPreviewTitle = this.root.querySelector("#kidcore-links-title");
    this.linkPreviewDescription = this.root.querySelector("#kidcore-links-description");
    this.linkPreviewUrl = this.root.querySelector("#kidcore-links-url");
    this.linkPreviewNote = this.root.querySelector("#kidcore-links-note");
    this.linkPreviewAction = this.root.querySelector("#kidcore-links-action");

    this.statusNote = this.root.querySelector("#kidcore-homeboard-status");

    this.boundWindowDragMove = (event) => {
      this.handleWindowDragMove(event);
    };
    this.boundWindowDragEnd = (event) => {
      this.handleWindowDragEnd(event);
    };

    this.themeObserver = new MutationObserver(() => {
      this.syncVisibility();
    });
    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    this.bindEvents();
    this.syncVisibility();
    this.render();
  }

  bindEvents() {
    this.tabButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const tabName = button.getAttribute("data-kidcore-tab") || "guestbook";
        this.setActiveTab(tabName);
        this.playClick();
      });
    });

    this.guestbookForm?.addEventListener("submit", (event) => {
      event.preventDefault();
      this.handleGuestbookSubmit();
    });

    this.webringPrevButton?.addEventListener("click", () => {
      this.selectWebringIndex(this.state.webringIndex - 1);
      this.playClick();
    });

    this.webringRandomButton?.addEventListener("click", () => {
      this.selectRandomWebringSite();
      this.playClick();
    });

    this.webringNextButton?.addEventListener("click", () => {
      this.selectWebringIndex(this.state.webringIndex + 1);
      this.playClick();
    });

    this.webringVisitButton?.addEventListener("click", () => {
      this.playClick();
      this.setStatusNote(`pretending to visit ${this.currentWebringSite().title.toLowerCase()}...`);
    });

    this.linkButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const linkIndex = Number(button.getAttribute("data-kidcore-link") || "0");
        this.selectLinkIndex(linkIndex);
        this.playClick();
      });
    });

    this.collapseButton?.addEventListener("click", () => {
      this.toggleWindowCollapse();
      this.playClick();
    });

    this.closeButton?.addEventListener("click", () => {
      this.closeWindow();
      this.playClick();
    });

    this.launcherButton?.addEventListener("click", () => {
      this.openWindow();
      this.playClick();
    });

    this.titlebar?.addEventListener("pointerdown", (event) => {
      this.handleTitlebarPointerDown(event);
    });

    this.titlebar?.addEventListener("click", (event) => {
      if (!this.matchesCompactViewport()) {
        return;
      }

      const target = event.target;
      if (target instanceof Element && target.closest("button")) {
        return;
      }

      this.toggleWindowCollapse();
      this.playClick();
    });

    this.titlebar?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      event.preventDefault();
      this.toggleWindowCollapse();
      this.playClick();
    });
  }

  playClick() {
    window.kidcoreAudioManager?.playClick?.();
  }

  playSuccess() {
    window.kidcoreAudioManager?.playSuccess?.();
  }

  playSend() {
    window.kidcoreAudioManager?.playSend?.();
  }

  matchesCompactViewport() {
    return this.isCompactViewport?.matches ?? window.innerWidth <= 720;
  }

  getWindowPosition() {
    if (!this.window) {
      return {
        left: this.state.windowLeft,
        top: this.state.windowTop,
      };
    }

    const rect = this.window.getBoundingClientRect();
    return {
      left: Math.round(rect.left),
      top: Math.round(rect.top),
    };
  }

  clampWindowPosition(left, top) {
    if (!this.window) {
      return { left, top };
    }

    const rect = this.window.getBoundingClientRect();
    const width = rect.width || this.window.offsetWidth || 0;
    const height = rect.height || this.window.offsetHeight || 0;
    const maxLeft = Math.max(16, window.innerWidth - width - 16);
    const maxTop = Math.max(84, window.innerHeight - height - 16);

    return {
      left: Math.min(Math.max(16, left), maxLeft),
      top: Math.min(Math.max(84, top), maxTop),
    };
  }

  syncWindowPosition() {
    if (!this.window) {
      return;
    }

    if (this.matchesCompactViewport() || this.state.windowState === "closed") {
      this.window.style.removeProperty("left");
      this.window.style.removeProperty("top");
      return;
    }

    const position = this.clampWindowPosition(this.state.windowLeft, this.state.windowTop);
    this.state.windowLeft = position.left;
    this.state.windowTop = position.top;
    this.window.style.left = `${position.left}px`;
    this.window.style.top = `${position.top}px`;
  }

  setWindowState(nextState, { save = true } = {}) {
    if (!["open", "collapsed", "closed"].includes(nextState)) {
      return;
    }

    this.state.windowState = nextState;
    if (nextState !== "closed") {
      const position = this.clampWindowPosition(this.state.windowLeft, this.state.windowTop);
      this.state.windowLeft = position.left;
      this.state.windowTop = position.top;
    }

    if (save) {
      this.saveState();
    }

    this.syncVisibility();
  }

  openWindow() {
    this.setWindowState("open");
  }

  closeWindow() {
    this.setWindowState("closed");
  }

  toggleWindowCollapse() {
    if (this.state.windowState === "closed") {
      this.openWindow();
      return;
    }

    this.setWindowState(this.state.windowState === "collapsed" ? "open" : "collapsed");
  }

  handleTitlebarPointerDown(event) {
    if (this.matchesCompactViewport() || !this.window || this.state.windowState === "closed") {
      return;
    }

    if (event.button !== 0) {
      return;
    }

    const target = event.target;
    if (target instanceof Element && target.closest("button")) {
      return;
    }

    event.preventDefault();
    this.dragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startLeft: this.getWindowPosition().left,
      startTop: this.getWindowPosition().top,
    };

    window.addEventListener("pointermove", this.boundWindowDragMove);
    window.addEventListener("pointerup", this.boundWindowDragEnd);
    window.addEventListener("pointercancel", this.boundWindowDragEnd);
  }

  handleWindowDragMove(event) {
    if (!this.dragState || event.pointerId !== this.dragState.pointerId || !this.window) {
      return;
    }

    event.preventDefault();
    const nextLeft = this.dragState.startLeft + (event.clientX - this.dragState.startX);
    const nextTop = this.dragState.startTop + (event.clientY - this.dragState.startY);
    const position = this.clampWindowPosition(nextLeft, nextTop);
    this.state.windowLeft = position.left;
    this.state.windowTop = position.top;
    this.window.style.left = `${position.left}px`;
    this.window.style.top = `${position.top}px`;
  }

  handleWindowDragEnd(event) {
    if (
      !this.dragState ||
      (typeof event.pointerId === "number" && event.pointerId !== this.dragState.pointerId)
    ) {
      return;
    }

    window.removeEventListener("pointermove", this.boundWindowDragMove);
    window.removeEventListener("pointerup", this.boundWindowDragEnd);
    window.removeEventListener("pointercancel", this.boundWindowDragEnd);
    this.dragState = null;
    this.saveState();
  }

  syncVisibility() {
    const visible = isKidcoreThemeActive();
    const windowVisible = visible && this.state.windowState !== "closed";
    const bodyVisible = windowVisible && this.state.windowState === "open";

    if (this.window) {
      this.window.hidden = !windowVisible;
      this.window.setAttribute("aria-hidden", String(!windowVisible));
      this.window.dataset.windowState = this.state.windowState;
    }

    if (this.windowBody) {
      this.windowBody.hidden = !bodyVisible;
      this.windowBody.setAttribute("aria-hidden", String(!bodyVisible));
      this.windowBody.dataset.windowBodyState = bodyVisible ? "open" : "collapsed";
    }

    this.root.hidden = !bodyVisible;
    this.root.setAttribute("aria-hidden", String(!bodyVisible));
    this.root.dataset.windowBodyState = bodyVisible ? "open" : "collapsed";

    if (this.launcherButton) {
      this.launcherButton.hidden = !visible || this.state.windowState !== "closed";
      this.launcherButton.setAttribute(
        "aria-hidden",
        String(!visible || this.state.windowState !== "closed"),
      );
    }

    if (this.collapseButton) {
      const collapsed = this.state.windowState === "collapsed";
      this.collapseButton.textContent = collapsed ? "▢" : "—";
      this.collapseButton.setAttribute(
        "aria-label",
        collapsed ? "Expand scrapbook window" : "Collapse scrapbook window",
      );
    }

    this.syncWindowPosition();
  }

  setStatusNote(message) {
    if (this.statusNote) {
      this.statusNote.textContent = message;
    }
  }

  saveState() {
    writeJSON(HOMEBOARD_STORAGE_KEY, {
      activeTab: this.state.activeTab,
      webringIndex: this.state.webringIndex,
      linkIndex: this.state.linkIndex,
      windowState: this.state.windowState,
      windowLeft: this.state.windowLeft,
      windowTop: this.state.windowTop,
    });
  }

  saveGuestbookEntries() {
    writeJSON(GUESTBOOK_STORAGE_KEY, this.userGuestbookEntries);
  }

  setActiveTab(tabName) {
    if (!this.panels[tabName]) {
      return;
    }

    this.state.activeTab = tabName;
    this.saveState();
    this.renderTabs();
    this.renderPanels();
    this.setStatusNote(`opened ${tabName}`);
  }

  currentWebringSite() {
    return WEBRING_SITES[this.state.webringIndex % WEBRING_SITES.length];
  }

  selectWebringIndex(index) {
    const normalized =
      ((index % WEBRING_SITES.length) + WEBRING_SITES.length) % WEBRING_SITES.length;
    this.state.webringIndex = normalized;
    this.saveState();
    this.renderWebring();
    this.setActiveTab("webring");
  }

  selectRandomWebringSite() {
    if (WEBRING_SITES.length <= 1) {
      this.selectWebringIndex(0);
      return;
    }

    let nextIndex = this.state.webringIndex;
    while (nextIndex === this.state.webringIndex) {
      nextIndex = Math.floor(Math.random() * WEBRING_SITES.length);
    }

    this.selectWebringIndex(nextIndex);
  }

  selectLinkIndex(index) {
    const normalized = ((index % LINK_CARDS.length) + LINK_CARDS.length) % LINK_CARDS.length;
    this.state.linkIndex = normalized;
    this.saveState();
    this.renderLinks();
    this.setActiveTab("links");
  }

  handleGuestbookSubmit() {
    const name = (this.guestbookNameInput?.value || "Anonymous").trim() || "Anonymous";
    const message = (this.guestbookMessageInput?.value || "").trim();
    if (!message) {
      return;
    }

    const entry = {
      name,
      message,
      createdAt: new Date().toISOString(),
    };

    this.userGuestbookEntries = [...this.userGuestbookEntries, entry];
    this.saveGuestbookEntries();
    this.renderGuestbook();
    this.playSend();
    this.playSuccess();
    this.setStatusNote("guestbook signed and tucked away for later");

    if (this.guestbookMessageInput) {
      this.guestbookMessageInput.value = "";
      this.guestbookMessageInput.focus();
    }
  }

  render() {
    this.renderTabs();
    this.renderPanels();
    this.renderGuestbook();
    this.renderWebring();
    this.renderLinks();
  }

  renderTabs() {
    this.tabButtons.forEach((button) => {
      const tabName = button.getAttribute("data-kidcore-tab") || "guestbook";
      const active = tabName === this.state.activeTab;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      button.setAttribute("tabindex", active ? "0" : "-1");
    });
  }

  renderPanels() {
    Object.entries(this.panels).forEach(([tabName, panel]) => {
      if (!panel) {
        return;
      }

      const active = tabName === this.state.activeTab;
      panel.hidden = !active;
      panel.classList.toggle("active", active);
      panel.setAttribute("aria-hidden", String(!active));
    });
  }

  renderGuestbook() {
    if (!this.guestbookEntriesList) {
      return;
    }

    const entries = [...DEFAULT_GUESTBOOK_ENTRIES, ...this.userGuestbookEntries];
    this.guestbookEntriesList.innerHTML = "";

    entries.forEach((entry) => {
      const item = createElement("li", "kidcore-guestbook-entry");
      const header = createElement("div", "kidcore-guestbook-entry-header");
      const name = createElement("strong", "kidcore-entry-name", entry.name);
      const time = createElement("span", "kidcore-entry-time", formatTimestamp(entry.createdAt));
      header.append(name, time);

      const message = createElement("p", "kidcore-entry-message", entry.message);
      item.append(header, message);
      this.guestbookEntriesList.appendChild(item);
    });
  }

  renderWebring() {
    const site = this.currentWebringSite();
    const position = `${this.state.webringIndex + 1} of ${WEBRING_SITES.length}`;
    if (this.webringPosition) {
      this.webringPosition.textContent = position;
    }
    if (this.webringTitle) {
      this.webringTitle.textContent = site.title;
    }
    if (this.webringDescription) {
      this.webringDescription.textContent = site.description;
    }
    if (this.webringUrl) {
      this.webringUrl.textContent = site.url;
    }
    if (this.webringNote) {
      this.webringNote.textContent = site.note;
    }
  }

  renderLinks() {
    const selected = LINK_CARDS[this.state.linkIndex];
    this.linkButtons.forEach((button) => {
      const index = Number(button.getAttribute("data-kidcore-link") || "0");
      button.classList.toggle("active", index === this.state.linkIndex);
      button.setAttribute("aria-pressed", String(index === this.state.linkIndex));
    });

    if (this.linkPreviewTitle) {
      this.linkPreviewTitle.textContent = selected.title;
    }
    if (this.linkPreviewDescription) {
      this.linkPreviewDescription.textContent = selected.description;
    }
    if (this.linkPreviewUrl) {
      this.linkPreviewUrl.textContent = selected.url;
    }
    if (this.linkPreviewNote) {
      this.linkPreviewNote.textContent = selected.note;
    }
    if (this.linkPreviewAction) {
      this.linkPreviewAction.textContent = `open ${selected.label}`;
    }
  }
}

let kidcoreHomeboard = null;

function initKidcoreHomeboard() {
  const root = document.getElementById("kidcore-homeboard");
  if (!root || kidcoreHomeboard) {
    return kidcoreHomeboard;
  }

  kidcoreHomeboard = new KidcoreHomeboard(root);
  window.__alfredKidcoreSite = {
    getState: () => ({
      ...kidcoreHomeboard.state,
      guestbookEntries: [...DEFAULT_GUESTBOOK_ENTRIES, ...kidcoreHomeboard.userGuestbookEntries],
    }),
    selectTab: (tabName) => kidcoreHomeboard.setActiveTab(tabName),
    selectWebringIndex: (index) => kidcoreHomeboard.selectWebringIndex(index),
    selectRandomWebringSite: () => kidcoreHomeboard.selectRandomWebringSite(),
    selectLinkIndex: (index) => kidcoreHomeboard.selectLinkIndex(index),
    openWindow: () => kidcoreHomeboard.openWindow(),
    closeWindow: () => kidcoreHomeboard.closeWindow(),
    toggleWindowCollapse: () => kidcoreHomeboard.toggleWindowCollapse(),
    addGuestbookEntry: (name, message) => {
      kidcoreHomeboard.guestbookNameInput.value = name;
      kidcoreHomeboard.guestbookMessageInput.value = message;
      kidcoreHomeboard.handleGuestbookSubmit();
    },
  };
  return kidcoreHomeboard;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initKidcoreHomeboard);
} else {
  initKidcoreHomeboard();
}

export { initKidcoreHomeboard };
