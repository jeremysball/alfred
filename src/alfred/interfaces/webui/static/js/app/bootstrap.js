/**
 * Bootstrap - Deterministic Web UI startup entrypoint
 *
 * Responsibilities:
 * - Wait for document readiness
 * - Track ordered initialization phases
 * - Initialize core runtime (chat, composer, WebSocket)
 * - Initialize optional features through explicit registration
 * - Expose bootstrap status for observability and testing
 *
 * Startup contract:
 * 1. Shell scripts load (config, logger) before this module
 * 2. This module initializes phases in order
 * 3. Core phases must complete before optional phases
 * 4. Failures are reported locally with phase information
 */

/**
 * Bootstrap phase tracking for observability and testing
 * @typedef {Object} BootstrapState
 * @property {'initializing'|'ready'|'failed'} status
 * @property {string} currentPhase
 * @property {Array<{name: string, completed: boolean, error?: string}>} phases
 * @property {string|null} failedPhase
 * @property {string|null} error
 */

const BOOTSTRAP_PHASES = {
  CORE: [
    "dom-ready",
    "config-available",
    "services-initialized",
    "components-registered",
    "websocket-connected",
    "chat-runtime-ready",
  ],
  OPTIONAL: [
    "keyboard-shortcuts",
    "command-palette",
    "search-features",
    "context-menus",
    "notifications",
    "drag-drop",
    "mobile-gestures",
    "offline-features",
    "pwa-features",
    "kidcore-features",
  ],
};

/**
 * Create initial bootstrap state
 * @returns {BootstrapState}
 */
function createInitialState() {
  const allPhases = [
    ...BOOTSTRAP_PHASES.CORE.map((name) => ({ name, completed: false })),
    ...BOOTSTRAP_PHASES.OPTIONAL.map((name) => ({ name, completed: false, optional: true })),
  ];

  return {
    status: "initializing",
    currentPhase: "pending",
    phases: allPhases,
    failedPhase: null,
    error: null,
  };
}

/**
 * Bootstrap controller
 */
class Bootstrap {
  constructor() {
    this.state = createInitialState();
    this.stepRegistry = new Map();
    this.initialized = false;
  }

  /**
   * Register an initialization step
   * @param {string} phase - Phase name from BOOTSTRAP_PHASES
   * @param {Function} fn - Async function to execute
   * @param {Object} options
   * @param {boolean} [options.optional=false] - Whether failure is fatal
   */
  registerStep(phase, fn, options = {}) {
    if (this.initialized) {
      throw new Error(`Cannot register step '${phase}' after bootstrap has started`);
    }
    this.stepRegistry.set(phase, { fn, optional: options.optional ?? false });
  }

  /**
   * Update phase status
   * @param {string} phaseName
   * @param {'completed'|'failed'} status
   * @param {string} [error]
   */
  updatePhase(phaseName, status, error = null) {
    const phase = this.state.phases.find((p) => p.name === phaseName);
    if (phase) {
      phase.completed = status === "completed";
      if (error) {
        phase.error = error;
      }
    }
    this.state.currentPhase = phaseName;
  }

  /**
   * Execute a single phase
   * @param {string} phaseName
   * @returns {Promise<boolean>}
   */
  async executePhase(phaseName) {
    const step = this.stepRegistry.get(phaseName);
    if (!step) {
      // Phase exists in list but no step registered - that's OK, just mark completed
      this.updatePhase(phaseName, "completed");
      return true;
    }

    this.state.currentPhase = phaseName;

    try {
      await step.fn();
      this.updatePhase(phaseName, "completed");
      return true;
    } catch (err) {
      this.updatePhase(phaseName, "failed", err.message);
      if (!step.optional) {
        this.state.status = "failed";
        this.state.failedPhase = phaseName;
        this.state.error = err.message;
        console.error(`[bootstrap] Core phase '${phaseName}' failed:`, err);
        return false;
      }
      // Optional phase failed - log but continue
      console.warn(`[bootstrap] Optional phase '${phaseName}' failed:`, err);
      return true;
    }
  }

  /**
   * Run all bootstrap phases
   * @returns {Promise<boolean>}
   */
  async run() {
    if (this.initialized) {
      console.warn("[bootstrap] Already initialized");
      return this.state.status === "ready";
    }

    this.initialized = true;
    console.log("[bootstrap] Starting initialization...");

    // Execute core phases first - these must all succeed
    for (const phaseName of BOOTSTRAP_PHASES.CORE) {
      const success = await this.executePhase(phaseName);
      if (!success) {
        console.error(`[bootstrap] Failed at core phase: ${phaseName}`);
        this._exposeState();
        return false;
      }
    }

    // Execute optional phases - failures don't block ready state
    for (const phaseName of BOOTSTRAP_PHASES.OPTIONAL) {
      await this.executePhase(phaseName);
    }

    this.state.status = "ready";
    this.state.currentPhase = "ready";
    console.log("[bootstrap] Initialization complete");

    this._exposeState();
    return true;
  }

  /**
   * Expose bootstrap state on window for observability and testing
   * @private
   */
  _exposeState() {
    // Ensure window.__alfredWebUI exists
    if (typeof window !== "undefined") {
      if (!window.__alfredWebUI) {
        window.__alfredWebUI = {};
      }
      window.__alfredWebUI.bootstrap = {
        status: this.state.status,
        currentPhase: this.state.currentPhase,
        phases: [...this.state.phases],
        failedPhase: this.state.failedPhase,
        error: this.state.error,
        // Helper for tests to wait for ready
        whenReady: () => {
          return new Promise((resolve, reject) => {
            if (this.state.status === "ready") {
              resolve();
              return;
            }
            if (this.state.status === "failed") {
              reject(
                new Error(`Bootstrap failed at ${this.state.failedPhase}: ${this.state.error}`),
              );
              return;
            }
            // Poll for status change
            const check = setInterval(() => {
              if (this.state.status === "ready") {
                clearInterval(check);
                resolve();
              } else if (this.state.status === "failed") {
                clearInterval(check);
                reject(
                  new Error(`Bootstrap failed at ${this.state.failedPhase}: ${this.state.error}`),
                );
              }
            }, 100);
          });
        },
      };
    }
  }
}

// Singleton bootstrap instance
const bootstrap = new Bootstrap();

/**
 * Wait for DOM to be ready
 * @returns {Promise<void>}
 */
function waitForDomReady() {
  return new Promise((resolve) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", resolve);
    } else {
      resolve();
    }
  });
}

/**
 * Default bootstrap configuration
 * These steps will be registered if no custom configuration is provided
 */
function registerDefaultSteps() {
  // Core phases
  bootstrap.registerStep("dom-ready", async () => {
    await waitForDomReady();
  });

  bootstrap.registerStep("config-available", async () => {
    // Config should be available from shell scripts
    if (!window.__ALFRED_WEBUI_CONFIG__) {
      console.warn("[bootstrap] __ALFRED_WEBUI_CONFIG__ not found, using defaults");
    }
  });

  bootstrap.registerStep("services-initialized", async () => {
    // WebSocket client and core services will be initialized here
    // For now, this is a placeholder - actual implementation in later phases
  });

  bootstrap.registerStep("components-registered", async () => {
    // Custom element registration will happen here
    // For now, this is a placeholder - actual implementation in later phases
  });

  bootstrap.registerStep("websocket-connected", async () => {
    // WebSocket connection will be established here
    // For now, this is a placeholder - actual implementation in later phases
  });

  bootstrap.registerStep("chat-runtime-ready", async () => {
    // Chat UI and composer initialization will happen here
    // For now, this is a placeholder - actual implementation in later phases
  });

  // Optional phases - marked as optional so they don't block ready state
  const optionalPhases = [
    "keyboard-shortcuts",
    "command-palette",
    "search-features",
    "context-menus",
    "notifications",
    "drag-drop",
    "mobile-gestures",
    "offline-features",
    "pwa-features",
    "kidcore-features",
  ];

  for (const phase of optionalPhases) {
    bootstrap.registerStep(
      phase,
      async () => {
        // Placeholder - actual implementation in later phases
        console.log(`[bootstrap] Optional phase '${phase}' (placeholder)`);
      },
      { optional: true },
    );
  }
}

/**
 * Start the bootstrap process
 * This is the main entrypoint that should be called after shell scripts load
 * @returns {Promise<boolean>}
 */
async function startBootstrap() {
  registerDefaultSteps();
  return await bootstrap.run();
}

// Expose bootstrap API
try {
  if (typeof window !== "undefined") {
    window.AlfredBootstrap = {
      start: startBootstrap,
      registerStep: (phase, fn, options) => bootstrap.registerStep(phase, fn, options),
      getState: () => ({ ...bootstrap.state }),
    };
  }
} catch (e) {
  console.error("[bootstrap] Failed to expose bootstrap API:", e);
}

export { BOOTSTRAP_PHASES, bootstrap, startBootstrap, waitForDomReady };

// Auto-start bootstrap when module loads (for Phase 1 contract establishment)
// In later phases, this will be called explicitly from the shell entrypoint
if (typeof window !== "undefined") {
  // Use setTimeout to ensure shell scripts (config, logger) have loaded
  setTimeout(() => {
    startBootstrap().then((success) => {
      if (success) {
        console.log("[bootstrap] Auto-start complete");
      } else {
        console.error("[bootstrap] Auto-start failed");
      }
    });
  }, 0);
}
