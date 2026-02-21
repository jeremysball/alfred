/**
 * Interactive Terminal Tool for AI Agent E2E Testing
 *
 * Uses VHS (Charmbracelet) to provide interactive terminal control
 * with screenshot capture and text extraction for TUI testing.
 *
 * PRD: https://github.com/jeremysball/alfred/issues/83
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type, Static } from "@sinclair/typebox";
import { StringEnum } from "@mariozechner/pi-ai";
import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";

// Schema for tool parameters
const TerminalToolParams = Type.Object({
  action: StringEnum(["start", "send", "capture", "exit"] as const, {
    description: "Action to perform",
  }),
  command: Type.Optional(
    Type.String({ description: "Command to run (for start action)" })
  ),
  keys: Type.Optional(
    Type.Array(Type.String(), { description: "Keystrokes to send (for send action)" })
  ),
  text: Type.Optional(
    Type.String({ description: "Text to type (for send action)" })
  ),
  sleep_ms: Type.Optional(
    Type.Number({ description: "Milliseconds to sleep (for send action)" })
  ),
  wait_pattern: Type.Optional(
    Type.String({ description: "Regex pattern to wait for before capture (for capture action)" })
  ),
});

type TerminalToolInput = Static<typeof TerminalToolParams>;

// Session state
interface SessionState {
  tempDir: string;
  tapeCommands: string[];
  command: string;
  screenshotCount: number;
}

let session: SessionState | null = null;

// Key name mappings (VHS expects specific names)
const KEY_MAPPINGS: Record<string, string> = {
  enter: "Enter",
  return: "Enter",
  tab: "Tab",
  space: "Space",
  backspace: "Backspace",
  delete: "Backspace",
  escape: "Escape",
  esc: "Escape",
  up: "Up",
  down: "Down",
  left: "Left",
  right: "Right",
  ctrl_c: "Ctrl+C",
  ctrl_d: "Ctrl+D",
  ctrl_z: "Ctrl+Z",
  ctrl_l: "Ctrl+L",
  ctrl_a: "Ctrl+A",
  ctrl_e: "Ctrl+E",
  ctrl_k: "Ctrl+K",
  ctrl_u: "Ctrl+U",
  ctrl_w: "Ctrl+W",
  ctrl_r: "Ctrl+R",
  home: "Home",
  end: "End",
  pageup: "PageUp",
  pagedown: "PageDown",
};

// VHS executable path
function getVhsPath(): string {
  // Check GOPATH first, then PATH
  const gopath = process.env.GOPATH || path.join(os.homedir(), "go");
  const vhsInGo = path.join(gopath, "bin", "vhs");
  if (fs.existsSync(vhsInGo)) return vhsInGo;

  // Fall back to "vhs" in PATH
  return "vhs";
}

// Create temp directory for session
function createTempDir(): string {
  const baseDir = path.join(os.tmpdir(), "pi-terminal");
  if (!fs.existsSync(baseDir)) {
    fs.mkdirSync(baseDir, { recursive: true });
  }
  const tempDir = fs.mkdtempSync(path.join(baseDir, "session-"));
  return tempDir;
}

// Parse text output from VHS .txt file
function parseTextOutput(content: string): string {
  // Split on frame separators (lines of dashes), take last non-empty frame
  const frames = content.split(/^──+$/m);
  const lastFrame = frames.map(f => f.trim()).filter(f => f.length > 0).pop() || "";
  return lastFrame;
}

// Truncate text output to avoid context bloat
function truncateText(text: string, maxBytes: number = 50000): string {
  if (Buffer.byteLength(text, "utf8") <= maxBytes) {
    return text;
  }

  // Truncate and add notice
  const truncated = text.slice(0, maxBytes);
  return truncated + "\n\n[Output truncated: too large]";
}

// Execute VHS with the current tape
async function executeVhs(
  tapeContent: string,
  tempDir: string,
  signal?: AbortSignal
): Promise<{ success: boolean; error?: string; textPath?: string }> {
  const tapePath = path.join(tempDir, "session.tape");

  try {
    // Write tape file
    fs.writeFileSync(tapePath, tapeContent);

    // Set up environment
    const env = {
      ...process.env,
      VHS_NO_SANDBOX: "true", // Required for containers
    };

    // Run VHS
    const { spawn } = await import("node:child_process");
    const vhsPath = getVhsPath();

    return new Promise((resolve) => {
      const proc = spawn(vhsPath, [tapePath], {
        cwd: tempDir,
        env,
        stdio: ["ignore", "pipe", "pipe"],
      });

      let stdout = "";
      let stderr = "";

      proc.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      proc.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      proc.on("close", (code) => {
        if (code === 0) {
          resolve({
            success: true,
            textPath: path.join(tempDir, "output.txt"),
          });
        } else {
          resolve({
            success: false,
            error: `VHS exited with code ${code}: ${stderr || stdout}`,
          });
        }
      });

      proc.on("error", (err) => {
        resolve({
          success: false,
          error: `Failed to run VHS: ${err.message}`,
        });
      });

      // Handle abort
      if (signal) {
        signal.addEventListener("abort", () => {
          proc.kill("SIGTERM");
          resolve({
            success: false,
            error: "Aborted",
          });
        });
      }
    });
  } catch (err: any) {
    return {
      success: false,
      error: `Failed to execute VHS: ${err.message}`,
    };
  }
}

// Build tape content from accumulated commands
function buildTape(commands: string[]): string {
  const header = [
    "# Generated by terminal tool",
    "Output output.txt",
    "Set TypingSpeed 50ms",
    "Set Shell bash",
    "",
  ].join("\n");

  return header + commands.join("\n") + "\n";
}

// Tool implementation
export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "terminal",
    label: "Interactive Terminal",
    description:
      "Interactive terminal control for E2E testing of TUI applications. " +
      "Actions: start(command) to begin, send(text?, keys?, sleep_ms?) to input, " +
      "capture(wait_pattern?) for screenshot+text, exit to cleanup. " +
      "Example: start('alfred') -> send('hello', ['Enter'], 10000) -> capture() -> exit(). " +
      "Use sleep_ms for slow operations (LLM responses need 10s+). " +
      "Supported keys: Enter, Tab, Space, Backspace, Escape, Up, Down, Left, Right, Ctrl+C, Ctrl+D, etc.",
    parameters: TerminalToolParams,

    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const { action, command, keys, text, sleep_ms, wait_pattern } = params;

      switch (action) {
        case "start": {
          // Check for existing session
          if (session) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: "Error: Session already active. Call exit first.",
                },
              ],
              isError: true,
            };
          }

          if (!command) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: "Error: command is required for start action.",
                },
              ],
              isError: true,
            };
          }

          // Create session
          const tempDir = createTempDir();
          session = {
            tempDir,
            tapeCommands: [],
            command,
            screenshotCount: 0,
          };

          // Initial tape commands: type the command and press Enter
          session.tapeCommands.push(`Type "${command}"`);
          session.tapeCommands.push("Enter");
          session.tapeCommands.push("Sleep 500ms"); // Wait for command to start

          return {
            content: [
              {
                type: "text" as const,
                text: `Session started.\nCommand: ${command}\nTemp dir: ${tempDir}\n\nUse 'send' to interact, 'capture' to get screenshot/text, 'exit' to close.`,
              },
            ],
            details: {
              tempDir,
              command,
            },
          };
        }

        case "send": {
          if (!session) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: "Error: No active session. Call start first.",
                },
              ],
              isError: true,
            };
          }

          const commands: string[] = [];

          // Process text input FIRST (type before pressing keys)
          if (text) {
            // Escape quotes in text
            const escaped = text.replace(/"/g, '\\"');
            commands.push(`Type "${escaped}"`);
          }

          // Process keystrokes AFTER text (e.g., Enter to submit)
          if (keys && keys.length > 0) {
            for (const key of keys) {
              const normalized = key.toLowerCase().replace(/[-_]/g, "_");
              const vhsKey = KEY_MAPPINGS[normalized];

              if (vhsKey) {
                commands.push(vhsKey);
              } else {
                // Unknown key - treat as single character or error
                if (key.length === 1) {
                  commands.push(`Type "${key}"`);
                } else {
                  return {
                    content: [
                      {
                        type: "text" as const,
                        text: `Error: Unknown key '${key}'. Supported keys: ${Object.keys(KEY_MAPPINGS).join(", ")}`,
                      },
                    ],
                    isError: true,
                  };
                }
              }
              commands.push("Sleep 50ms"); // Small delay between keystrokes
            }
          }

          // Process sleep LAST (wait for response)
          if (sleep_ms) {
            commands.push(`Sleep ${sleep_ms}ms`);
          }

          if (commands.length === 0) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: "Error: At least one of keys, text, or sleep_ms is required for send action.",
                },
              ],
              isError: true,
            };
          }

          session.tapeCommands.push(...commands);

          return {
            content: [
              {
                type: "text" as const,
                text: `Sent: ${keys?.length ? `${keys.length} keystrokes` : ""}${keys?.length && text ? " + " : ""}${text ? `text "${text}"` : ""}${(keys?.length || text) && sleep_ms ? " + " : ""}${sleep_ms ? `sleep ${sleep_ms}ms` : ""}`,
              },
            ],
            details: {
              keys,
              text,
            },
          };
        }

        case "capture": {
          if (!session) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: "Error: No active session. Call start first.",
                },
              ],
              isError: true,
            };
          }

          // Increment screenshot counter
          session.screenshotCount++;
          const screenshotPath = path.join(
            session.tempDir,
            `screenshot_${session.screenshotCount}.png`
          );

          // Add wait if pattern provided
          if (wait_pattern) {
            session.tapeCommands.push(`Wait /${wait_pattern}/`);
          } else {
            // Default small wait before capture
            session.tapeCommands.push("Sleep 500ms");
          }

          // Add screenshot command
          session.tapeCommands.push(`Screenshot ${path.basename(screenshotPath)}`);

          // Build and execute tape
          const tapeContent = buildTape(session.tapeCommands);

          onUpdate?.({
            content: [{ type: "text", text: "Capturing terminal state..." }],
          });

          const result = await executeVhs(tapeContent, session.tempDir, signal);

          if (!result.success) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: `Error: ${result.error}`,
                },
              ],
              isError: true,
            };
          }

          // Read and parse text output
          let textOutput = "";
          if (result.textPath && fs.existsSync(result.textPath)) {
            const rawText = fs.readFileSync(result.textPath, "utf-8");
            textOutput = truncateText(parseTextOutput(rawText));
          }

          // Verify screenshot exists
          if (!fs.existsSync(screenshotPath)) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: `Error: Screenshot was not created at ${screenshotPath}`,
                },
              ],
              isError: true,
            };
          }

          return {
            content: [
              {
                type: "text" as const,
                text: `Capture complete.\n\nScreenshot: ${screenshotPath}\n\nText output:\n${textOutput}`,
              },
            ],
            details: {
              screenshot: screenshotPath,
              text: textOutput,
            },
          };
        }

        case "exit": {
          if (!session) {
            return {
              content: [
                {
                  type: "text" as const,
                  text: "Error: No active session. Call start first.",
                },
              ],
              isError: true,
            };
          }

          // Send Ctrl+C to ensure clean exit
          session.tapeCommands.push("Ctrl+C");
          session.tapeCommands.push("Sleep 200ms");

          // Execute final tape
          const tapeContent = buildTape(session.tapeCommands);

          onUpdate?.({
            content: [{ type: "text", text: "Closing session..." }],
          });

          await executeVhs(tapeContent, session.tempDir, signal);

          // Cleanup temp directory
          try {
            fs.rmSync(session.tempDir, { recursive: true, force: true });
          } catch (err: any) {
            // Non-fatal - just log
            console.error(`Failed to cleanup temp dir: ${err.message}`);
          }

          const summary = {
            command: session.command,
            screenshots: session.screenshotCount,
            tempDir: session.tempDir,
          };

          session = null;

          return {
            content: [
              {
                type: "text" as const,
                text: `Session closed.\nCommand: ${summary.command}\nScreenshots taken: ${summary.screenshots}\nTemp dir cleaned up.`,
              },
            ],
            details: summary,
          };
        }

        default:
          return {
            content: [
              {
                type: "text" as const,
                text: `Error: Unknown action '${action}'`,
              },
            ],
            isError: true,
          };
      }
    },
  });

  // Cleanup on session shutdown
  pi.on("session_shutdown", async () => {
    if (session) {
      try {
        fs.rmSync(session.tempDir, { recursive: true, force: true });
      } catch (err: any) {
        console.error(`Failed to cleanup session on shutdown: ${err.message}`);
      }
      session = null;
    }
  });
}
