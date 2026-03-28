/**
 * Shared contrast utilities for Alfred Web UI.
 *
 * Standard pattern:
 * - Themes define surface background CSS variables
 * - We compute readable text colors at runtime from those backgrounds
 * - Components consume the computed --contrast-* variables
 */

/**
 * Calculate relative luminance of a color (WCAG 2.0).
 */
function getLuminance(r, g, b) {
  const rsRGB = r / 255;
  const gsRGB = g / 255;
  const bsRGB = b / 255;

  const rLinear = rsRGB <= 0.03928 ? rsRGB / 12.92 : ((rsRGB + 0.055) / 1.055) ** 2.4;
  const gLinear = gsRGB <= 0.03928 ? gsRGB / 12.92 : ((gsRGB + 0.055) / 1.055) ** 2.4;
  const bLinear = bsRGB <= 0.03928 ? bsRGB / 12.92 : ((bsRGB + 0.055) / 1.055) ** 2.4;

  return 0.2126 * rLinear + 0.7152 * gLinear + 0.0722 * bLinear;
}

function hexToRgb(hex) {
  const normalized = hex.replace("#", "").trim();

  if (normalized.length === 3) {
    const expanded = normalized
      .split("")
      .map((c) => c + c)
      .join("");
    return hexToRgb(`#${expanded}`);
  }

  if (normalized.length === 4) {
    const expanded = normalized
      .split("")
      .map((c) => c + c)
      .join("");
    return hexToRgb(`#${expanded}`);
  }

  const hasAlpha = normalized.length === 8;
  const bigint = Number.parseInt(normalized, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  const a = hasAlpha ? ((bigint >> 24) & 255) / 255 : 1;

  return [r, g, b, a];
}

function parseRgb(rgb) {
  const match = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (!match) {
    return [0, 0, 0, 1];
  }

  return [
    Number.parseInt(match[1], 10),
    Number.parseInt(match[2], 10),
    Number.parseInt(match[3], 10),
    match[4] ? Number.parseFloat(match[4]) : 1,
  ];
}

function getRgb(color) {
  const normalized = color.trim().toLowerCase();

  if (normalized.startsWith("#")) {
    return hexToRgb(normalized);
  }

  if (normalized.startsWith("rgb")) {
    return parseRgb(normalized);
  }

  if (typeof document === "undefined") {
    return [0, 0, 0, 1];
  }

  const temp = document.createElement("div");
  temp.style.color = normalized;
  temp.style.display = "none";
  document.body.appendChild(temp);
  const computed = getComputedStyle(temp).color;
  temp.remove();
  return parseRgb(computed);
}

function getContrastRatio(lum1, lum2) {
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

export function getContrastText(bgColor) {
  const [r, g, b, a] = getRgb(bgColor);
  const effectiveR = Math.round(r * a + 255 * (1 - a));
  const effectiveG = Math.round(g * a + 255 * (1 - a));
  const effectiveB = Math.round(b * a + 255 * (1 - a));

  const bgLuminance = getLuminance(effectiveR, effectiveG, effectiveB);
  const whiteContrast = getContrastRatio(bgLuminance, 1);
  const blackContrast = getContrastRatio(bgLuminance, 0);

  return whiteContrast >= blackContrast ? "#ffffff" : "#000000";
}

export function getContrastTextFromVar(cssVar, fallback = "#1a1a1a") {
  if (typeof document === "undefined") {
    return getContrastText(fallback);
  }

  const root = document.documentElement;
  const bgColor = getComputedStyle(root).getPropertyValue(cssVar).trim() || fallback;
  return getContrastText(bgColor);
}

export const CONTRAST_PRESETS = {
  "#e0e5ec": "#000000",
  "#f5f5f5": "#000000",
  "#ffffff": "#000000",
  "#eeeeee": "#000000",
  "#e8e2d9": "#1a1814",
  "#000000": "#ffffff",
  "#0a0a0a": "#ffffff",
  "#1a1a1a": "#ffffff",
  "#1a1814": "#e8e2d9",
  "#1a202c": "#e2e8f0",
  "#2d3748": "#e2e8f0",
};

export function getContrastTextFast(bgColor) {
  const normalized = bgColor.trim().toLowerCase();
  return CONTRAST_PRESETS[normalized] || getContrastText(normalized);
}

function pickCssVar(root, vars, fallback) {
  for (const cssVar of vars) {
    const value = getComputedStyle(root).getPropertyValue(cssVar).trim();
    if (value) return value;
  }
  return fallback;
}

export function getContrastPalette(bgColor, accentColor = null) {
  const text = getContrastTextFast(bgColor);
  const muted = text === "#ffffff" ? "#b0b0b0" : "#4a4a4a";
  const accent = accentColor || (text === "#ffffff" ? "#4fc3f7" : "#0066cc");

  return { text, muted, accent };
}

function setContrastVars(root, prefix, bgColor, accentColor = null) {
  const palette = getContrastPalette(bgColor, accentColor);

  root.style.setProperty(`--contrast-${prefix}-text`, palette.text);
  root.style.setProperty(`--contrast-${prefix}-muted`, palette.muted);
  root.style.setProperty(`--contrast-${prefix}-accent`, palette.accent);
}

/**
 * Apply the standard Alfred contrast system.
 *
 * This computes text colors for the major UI surfaces and exposes
 * the results as CSS custom properties.
 */
export function applyThemeContrast(root = document.documentElement) {
  if (typeof document === "undefined") {
    return;
  }

  const settingsBg = pickCssVar(
    root,
    ["--settings-bg", "--surface-panel-bg", "--surface-bg"],
    "#1a1a1a",
  );
  const toolBg = pickCssVar(
    root,
    ["--tool-bg", "--surface-tool-bg", "--surface-elevated-bg"],
    settingsBg,
  );
  const composerBg = pickCssVar(
    root,
    ["--composer-bg", "--message-input-bg", "--surface-input-bg"],
    settingsBg,
  );
  const statusBg = pickCssVar(
    root,
    ["--status-bg", "--surface-footer-bg", "--surface-bg"],
    settingsBg,
  );
  const sendBg = pickCssVar(root, ["--send-button-bg", "--surface-accent-bg"], composerBg);
  const statusSuccessBg = pickCssVar(
    root,
    ["--status-success-bg", "--status-connected-bg", "--accent-success-bg", "--md-accent-success"],
    sendBg,
  );
  const statusErrorBg = pickCssVar(
    root,
    ["--status-error-bg", "--status-disconnected-bg", "--accent-error-bg", "--md-accent-danger"],
    sendBg,
  );
  const statusRunningBg = pickCssVar(
    root,
    ["--status-running-bg", "--status-connecting-bg", "--accent-warning-bg", "--md-accent-warning"],
    sendBg,
  );

  setContrastVars(root, "settings", settingsBg);
  setContrastVars(root, "tool", toolBg);
  setContrastVars(root, "tool-running", pickCssVar(root, ["--tool-running-bg"], toolBg));
  setContrastVars(root, "tool-success", pickCssVar(root, ["--tool-success-bg"], toolBg));
  setContrastVars(root, "tool-error", pickCssVar(root, ["--tool-error-bg"], toolBg));
  setContrastVars(root, "composer", composerBg);
  setContrastVars(root, "status", statusBg);
  setContrastVars(root, "status-success", statusSuccessBg);
  setContrastVars(root, "status-error", statusErrorBg);
  setContrastVars(root, "status-running", statusRunningBg);
  setContrastVars(root, "send", sendBg);

  // Compatibility fallbacks used by existing selectors.
  const settingsText = getContrastTextFast(settingsBg);
  root.style.setProperty("--contrast-text", settingsText);
  root.style.setProperty("--contrast-muted", settingsText === "#ffffff" ? "#a0a0a0" : "#606060");
  root.style.setProperty("--contrast-accent", settingsText === "#ffffff" ? "#4fc3f7" : "#0066cc");
}

export function applyAutoContrast() {
  if (typeof document === "undefined") {
    return;
  }

  document.querySelectorAll("[data-auto-contrast]").forEach((el) => {
    const bgVar = el.dataset.autoContrast || "--bg-color";
    const textColor = getContrastTextFromVar(bgVar);
    el.style.color = textColor;
  });
}

export function getIconContrastFilter(baseColor) {
  const [r, g, b] = getRgb(baseColor);
  const luminance = getLuminance(r, g, b);
  return luminance > 0.5 ? "brightness(0)" : "brightness(0) invert(1)";
}
