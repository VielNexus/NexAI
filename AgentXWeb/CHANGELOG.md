# AgentXWeb Changelog

## V9 - State recovery, typecheck, and settings stabilization

- Restored TypeScript correctness for the V9 recovery build.
- Added Workbench import response typing for `thread_workspace`.
- Stopped storing full message arrays in thread-summary state.
- Fixed task-reflection API helpers to use the existing response handler.
- Fixed local-path composer attachment typing.
- Restored Settings page model-behavior update handling.
- Extended Settings status props for Ollama endpoint/refresh metadata.
- Changed `npm run build` to run TypeScript checking before the Vite production build.

Validation performed in this patch workspace:

- `node node_modules/typescript/bin/tsc -p tsconfig.json --noEmit`: passed
- `node node_modules/vitest/vitest.mjs run`: passed, 6 files / 21 tests
- `node node_modules/vite/bin/vite.js build`: passed

Note: this archive had broken `node_modules/.bin` launcher files after ZIP extraction, so validation used direct Node entrypoints. On the VM, run `npm ci` to restore normal `.bin` links before using `npm test` or `npm run build`.
