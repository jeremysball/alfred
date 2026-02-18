/**
 * Todo-List Extension with Collapsible Sidebar
 *
 * Features:
 * - Collapsible sidebar displaying todo list
 * - Add, toggle, and clear todos via LLM tool
 * - Persistent state across session branches
 * - Commands: /todo (open sidebar), /todo-toggle (collapse/expand)
 */

import { StringEnum } from "@mariozechner/pi-ai";
import type { ExtensionAPI, ExtensionContext, Theme } from "@mariozechner/pi-coding-agent";
import { matchesKey, Text, truncateToWidth, type Component } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";

export interface Todo {
	id: number;
	text: string;
	done: boolean;
}

export interface TodoDetails {
	action: "list" | "add" | "toggle" | "clear";
	todos: Todo[];
	nextId: number;
	error?: string;
}

/**
 * TodoStore - Manages todo state
 * Used by tests and internal state management
 */
export class TodoStore {
	private todos: Todo[] = [];
	private nextId: number = 1;
	private onChangeCallback?: () => void;

	constructor() {
		// Initialize empty store
	}

	add(text: string): Todo {
		const todo: Todo = { id: this.nextId++, text, done: false };
		this.todos.push(todo);
		this.onChange();
		return todo;
	}

	toggle(id: number): boolean {
		const todo = this.todos.find((t) => t.id === id);
		if (!todo) return false;
		todo.done = !todo.done;
		this.onChange();
		return true;
	}

	clear(): void {
		this.todos = [];
		this.nextId = 1;
		this.onChange();
	}

	getAll(): Todo[] {
		return [...this.todos];
	}

	getCompletedCount(): number {
		return this.todos.filter((t) => t.done).length;
	}

	getPendingCount(): number {
		return this.todos.filter((t) => !t.done).length;
	}

	getState(): { todos: Todo[]; nextId: number } {
		return { todos: [...this.todos], nextId: this.nextId };
	}

	reconstruct(todos: Todo[], nextId: number): void {
		this.todos = [...todos];
		this.nextId = nextId;
	}

	setOnChange(callback: () => void): void {
		this.onChangeCallback = callback;
	}

	private onChange(): void {
		this.onChangeCallback?.();
	}
}

// Global store instance for extension
const store = new TodoStore();

// Module-level accessors for backward compatibility
let todos: Todo[] = [];
let nextId = 1;

const syncStateFromStore = () => {
	const state = store.getState();
	todos = state.todos;
	nextId = state.nextId;
};

const reconstructState = (ctx: ExtensionContext) => {
	store.clear();
	nextId = 1;

	for (const entry of ctx.sessionManager.getBranch()) {
		if (entry.type !== "message") continue;
		const msg = entry.message;
		if (msg.role !== "toolResult" || msg.toolName !== "todo-sidebar") continue;

		const details = msg.details as TodoDetails | undefined;
		if (details) {
			store.reconstruct(details.todos, details.nextId);
			syncStateFromStore();
		}
	}
};

// Session events
const setupSessionListeners = (pi: ExtensionAPI) => {
	pi.on("session_start", async (_event, ctx) => reconstructState(ctx));
	pi.on("session_switch", async (_event, ctx) => reconstructState(ctx));
	pi.on("session_fork", async (_event, ctx) => reconstructState(ctx));
	pi.on("session_tree", async (_event, ctx) => reconstructState(ctx));
};

// Tool parameters
const TodoParams = Type.Object({
	action: StringEnum(["list", "add", "toggle", "clear"] as const),
	text: Type.Optional(Type.String({ description: "Todo text (for add)" })),
	id: Type.Optional(Type.Number({ description: "Todo ID (for toggle)" })),
});

/**
 * UI Component for collapsible sidebar
 */
class SidebarWidget implements Component {
	private expanded: boolean;
	private todos: Todo[];
	private theme: Theme | undefined;
	private onClose: () => void;
	private lines: string[] = [];
	private cachedWidth?: number;

	constructor(todos: Todo[], expanded: boolean = true, theme: Theme | undefined, onClose: () => void) {
		this.todos = todos;
		this.expanded = expanded;
		this.theme = theme;
		this.onClose = onClose;
		this.renderLines(80);
	}

	updateTodos(newTodos: Todo[]): void {
		this.todos = newTodos;
		this.renderLines(this.cachedWidth);
	}

	private renderLines(width?: number): void {
		this.lines = [];

		if (!this.theme) {
			this.lines = ["Todo sidebar: theme not available"];
			return;
		}

		// Use provided width or default to 80
		const maxWidth = width || 80;

		if (this.expanded) {
			this.lines.push("");
			const title = this.theme.fg("accent", " Todos ");
			const borderChar = "─";
			const prefix = this.theme.fg("borderMuted", "──") + title;
			const suffixWidth = maxWidth - prefix.length - 2; // -2 for padding
			const suffix = suffixWidth > 0 ? this.theme.fg("borderMuted", borderChar.repeat(suffixWidth)) : "";
			this.lines.push(truncateToWidth(prefix + suffix, maxWidth));
			this.lines.push("");

			if (this.todos.length === 0) {
				this.lines.push(truncateToWidth(`  ${this.theme.fg("dim", "No todos yet. Ask the agent to add some!")}`, maxWidth));
			} else {
				const done = this.todos.filter((t) => t.done).length;
				const total = this.todos.length;
				this.lines.push(truncateToWidth(`  ${this.theme.fg("muted", `${done}/${total} completed`)}`, maxWidth));
				this.lines.push("");

				for (const todo of this.todos) {
					const check = todo.done ? this.theme.fg("success", "✓") : this.theme.fg("dim", "○");
					const id = this.theme.fg("accent", `#${todo.id}`);
					const text = todo.done ? this.theme.fg("dim", todo.text) : this.theme.fg("text", todo.text);
					this.lines.push(truncateToWidth(`  ${check} ${id} ${text}`, maxWidth));
				}
			}

			this.lines.push("");
			this.lines.push(truncateToWidth(`  ${this.theme.fg("dim", "Press Escape to close")}`, maxWidth));
			this.lines.push("");
		} else {
			const check = this.todos.length > 0 ? this.theme.fg("accent", "▼") : this.theme.fg("dim", "○");
			const countText = this.theme.fg("muted", `${this.todos.length} todo(s)`);
			this.lines.push(truncateToWidth(`  ${check} ${countText}`, maxWidth));
		}
	}

	setTheme(theme: Theme): void {
		this.theme = theme;
		this.renderLines(this.cachedWidth);
	}

	handleInput(data: string): void {
		if (matchesKey(data, "escape") || matchesKey(data, "ctrl+c")) {
			this.onClose();
		}
	}

	toggleExpanded(): void {
		this.expanded = !this.expanded;
		this.renderLines(this.cachedWidth);
	}

	isExpanded(): boolean {
		return this.expanded;
	}

	// Component interface methods
	invalidate(): void {
		this.cachedWidth = undefined;
		this.renderLines(this.cachedWidth);
	}

	render(width?: number): string[] {
		// If width changed, re-render lines
		if (width !== undefined && width !== this.cachedWidth) {
			this.cachedWidth = width;
			this.renderLines(width);
		}
		return this.lines;
	}

	onKey: ((key: string) => boolean) | undefined = (key: string) => {
		this.handleInput(key);
		return true;
	};
}

/**
 * Main extension function
 */
export default function (pi: ExtensionAPI) {
	// Setup session listeners for state persistence
	setupSessionListeners(pi);

	// Register the todo-sidebar tool for the LLM
	pi.registerTool({
		name: "todo-sidebar",
		label: "Todo Sidebar",
		description: "Manage todos with a collapsible sidebar. Actions: list, add (text), toggle (id), clear",
		parameters: TodoParams,

		async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
			switch (params.action) {
				case "list": {
					const allTodos = store.getAll();
					return {
						content: [
							{
								type: "text",
								text: allTodos.length
									? allTodos.map((t) => `[${t.done ? "x" : " "}] #${t.id}: ${t.text}`).join("\n")
									: "No todos",
							},
						],
						details: { action: "list", todos: allTodos, nextId: store.getState().nextId } as TodoDetails,
					};
				}

				case "add": {
					if (!params.text) {
						return {
							content: [{ type: "text", text: "Error: text required for add" }],
							details: { action: "add", todos: store.getAll(), nextId: store.getState().nextId, error: "text required" } as TodoDetails,
						};
					}
					const newTodo = store.add(params.text);
					syncStateFromStore();
					return {
						content: [{ type: "text", text: `Added todo #${newTodo.id}: ${newTodo.text}` }],
						details: { action: "add", todos: store.getAll(), nextId: store.getState().nextId } as TodoDetails,
					};
				}

				case "toggle": {
					if (params.id === undefined) {
						return {
							content: [{ type: "text", text: "Error: id required for toggle" }],
							details: { action: "toggle", todos: store.getAll(), nextId: store.getState().nextId, error: "id required" } as TodoDetails,
						};
					}
					const success = store.toggle(params.id);
					syncStateFromStore();
					if (!success) {
						return {
							content: [{ type: "text", text: `Todo #${params.id} not found` }],
							details: {
								action: "toggle",
								todos: store.getAll(),
								nextId: store.getState().nextId,
								error: `#${params.id} not found`,
							} as TodoDetails,
						};
					}
					const todo = store.getAll().find((t) => t.id === params.id);
					return {
						content: [{ type: "text", text: `Todo #${todo!.id} ${todo!.done ? "completed" : "uncompleted"}` }],
						details: { action: "toggle", todos: store.getAll(), nextId: store.getState().nextId } as TodoDetails,
					};
				}

				case "clear": {
					const count = store.getAll().length;
					store.clear();
					syncStateFromStore();
					return {
						content: [{ type: "text", text: `Cleared ${count} todos` }],
						details: { action: "clear", todos: [], nextId: 1 } as TodoDetails,
					};
				}

				default:
					return {
						content: [{ type: "text", text: `Unknown action: ${params.action}` }],
						details: {
							action: "list",
							todos: store.getAll(),
							nextId: store.getState().nextId,
							error: `unknown action: ${params.action}`,
						} as TodoDetails,
					};
			}
		},

		renderCall(args, theme) {
			if (!theme) return new Text("todo-sidebar " + args.action, 0, 0);
			let text = theme.fg("toolTitle", theme.bold("todo-sidebar ")) + theme.fg("muted", args.action);
			if (args.text) text += ` ${theme.fg("dim", `"${args.text}"`)}`;
			if (args.id !== undefined) text += ` ${theme.fg("accent", `#${args.id}`)}`;
			return new Text(text, 0, 0);
		},

		renderResult(result, { expanded }, theme) {
			const details = result.details as TodoDetails | undefined;
			if (!details) {
				const text = result.content[0];
				return new Text(text?.type === "text" ? text.text : "", 0, 0);
			}

			if (!theme) {
				return new Text(details.error ? `Error: ${details.error}` : "Todo updated", 0, 0);
			}

			if (details.error) {
				return new Text(theme.fg("error", `Error: ${details.error}`), 0, 0);
			}

			const todoList = details.todos;

			switch (details.action) {
				case "list": {
					if (!theme) return new Text(`${todoList.length} todo(s)`, 0, 0);
					if (todoList.length === 0) {
						return new Text(theme.fg("dim", "No todos"), 0, 0);
					}
					let listText = theme.fg("muted", `${todoList.length} todo(s):`);
					const display = expanded ? todoList : todoList.slice(0, 5);
					for (const t of display) {
						const check = t.done ? theme.fg("success", "✓") : theme.fg("dim", "○");
						const itemText = t.done ? theme.fg("dim", t.text) : theme.fg("muted", t.text);
						listText += `\n${check} ${theme.fg("accent", `#${t.id}`)} ${itemText}`;
					}
					if (!expanded && todoList.length > 5) {
						listText += `\n${theme.fg("dim", `... ${todoList.length - 5} more`)}`;
					}
					return new Text(listText, 0, 0);
				}

				case "add": {
					const added = todoList[todoList.length - 1];
					if (!theme) return new Text(`Added #${added.id}: ${added.text}`, 0, 0);
					return new Text(
						theme.fg("success", "✓ Added ") +
							theme.fg("accent", `#${added.id}`) +
							" " +
							theme.fg("muted", added.text),
						0,
						0,
					);
				}

				case "toggle": {
					const text = result.content[0];
					const msg = text?.type === "text" ? text.text : "";
					if (!theme) return new Text(msg, 0, 0);
					return new Text(theme.fg("success", "✓ ") + theme.fg("muted", msg), 0, 0);
				}

				case "clear":
					if (!theme) return new Text("Cleared all todos", 0, 0);
					return new Text(theme.fg("success", "✓ ") + theme.fg("muted", "Cleared all todos"), 0, 0);
			}
		},
	});

	// Register the /todo command for users to open the sidebar
	pi.registerCommand("todo", {
		description: "Show todo sidebar",
		handler: async (_args, ctx) => {
			if (!ctx.hasUI) {
				ctx.ui.notify("/todo requires interactive mode", "error");
				return;
			}

			// Show widget as a true sidebar overlay on the left side
			await ctx.ui.custom<void>((tui, theme, _kb, done) => {
				const widget = new SidebarWidget(store.getAll(), true, theme, () => {
					done();
				});

				return {
					render: (width: number) => widget.render(width),
					invalidate: () => widget.invalidate(),
					handleInput: (data: string) => widget.handleInput(data),
				};
			}, {
				overlay: true,
				overlayOptions: {
					width: "30%",        // 30% of terminal width
					anchor: "left-center", // Anchor to left side
					offsetX: 0,
					offsetY: 0,
				},
			});
		},
	});

	// Register the /todo-toggle command for collapsing/expanding the sidebar
	pi.registerCommand("todo-toggle", {
		description: "Toggle sidebar collapse/expand state",
		handler: async (_args, ctx) => {
			if (!ctx.hasUI) {
				ctx.ui.notify("/todo-toggle requires interactive mode", "error");
				return;
			}

			// For now, just notify user
			ctx.ui.notify("Sidebar toggle command - implementation in progress", "info");
		},
	});
}
