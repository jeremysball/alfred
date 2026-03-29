## Secrets and Authentication

- Do not reveal secret values in responses or logs unless the user explicitly asks.
- Prefer the project's existing auth and secret-loading mechanisms over ad-hoc exports.
- Avoid asking the user to paste secrets into chat if the environment or repo already provides them.
- Ask before actions that use credentials against external systems.
