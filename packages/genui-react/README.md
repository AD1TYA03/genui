# genui-react

React components for [genui](https://github.com/AD1TYA03/genui). Pair it with the `genui-py` backend to get a streaming generative UI chat in a few lines: the model answers with OpenUI Lang, and this package renders it as real components (cards, tables, charts, forms).

> Community project. Not affiliated with or endorsed by Thesys. Built on OpenUI's MIT-licensed renderer (`@openuidev/*`).

<p align="center">
  <a href="https://genui-py.vercel.app/wander"><img alt="Wander: a Gemini agent booking a stay, rendered with genui-react" src="https://raw.githubusercontent.com/AD1TYA03/genui/main/assets/wander.gif" width="760"></a>
  <br><sub>A real run: Python agent (genui-py) → React (genui-react). <a href="https://genui-py.vercel.app">Live demo</a></sub>
</p>

## Install

```bash
npm install genui-react react react-dom
pip install genui-py   # the Python backend
```

## Quick start

```tsx
import "genui-react/styles.css";
import { GenUIChat } from "genui-react";

export default function App() {
  return (
    <div style={{ height: "100vh" }}>
      <GenUIChat url="/api/chat" agentName="My assistant" />
    </div>
  );
}
```

`url` is the genui-py endpoint. It receives a POST with `{ threadId, runId, messages, tools, context }` and streams AG-UI events (SSE) back. Threads are saved in `localStorage`. See [`examples/fastapi-react`](https://github.com/AD1TYA03/genui/tree/main/examples/fastapi-react) for a full FastAPI + React app.

## Light entry: `genui-react/core`

The main entry includes OpenUI's default component library: charts, tables, code highlighting and math, about 970 KB gzipped with React. If you render your own components, import from `genui-react/core`. It's about **210 KB** with React, measured with a custom component library.

```tsx
import { GenUIRenderer, createLibrary, defineComponent, genuiLLM, ChatProvider } from "genui-react/core";

const library = createLibrary({ components: [Deal, Pipeline /* yours */], root: "Stack" });
<GenUIRenderer response={program} library={library} />;
```

`core` exports `GenUIRenderer` (with `library` required), `genuiLLM`, `localStorageChat`, `clearChatHistory`, `safeUrl`, `safeOpenUrl`, `createLibrary`, `defineComponent`, `defineAction`, `buildMessage`, `parseMessage`, and the headless chat state (`ChatProvider`, `useThread`, `useThreadList`, `restStorage`). It never imports `@openuidev/react-ui`, and a test checks this.

## API

### `<GenUIChat />`

The full chat UI: thread sidebar, composer, streaming replies rendered as components.

| Prop | Type | Default | |
| --- | --- | --- | --- |
| `url` | `string` | `"/api/chat"` | Backend endpoint. |
| `library` | `GenUILibrary` | `defaultLibrary` | Components the model may use. Must match the library the backend prompts with. |
| `agentName` | `string` | | Name shown in the chat chrome. |
| `logoUrl` | `string` | | Logo in the sidebar and mobile header. |
| `headers` | `Record<string, string>` | | Extra request headers, e.g. auth. |
| `body` | `Record<string, unknown>` | | Extra fields merged into each request body. |
| `format` | `"ag-ui" \| "openai"` | `"ag-ui"` | Stream format the backend speaks. |
| `storageKey` | `string \| false` | `"genui"` | `localStorage` namespace. `false` keeps history in memory. |
| `storage` | `GenUIStorage` | | Custom thread storage, e.g. `restStorage({ baseUrl })`. Overrides `storageKey`. |
| `llm` | `GenUILLM` | | Custom transport. Overrides `url`, `headers`, `body`, `format`. |
| `theme` | `"light" \| "dark" \| GenUIThemeProps` | | Color mode or full theme overrides. |
| `starters` | `GenUIStarter[]` | | Conversation starters on the welcome screen. |
| `onAction` | `(event) => void` | | Custom actions fired by rendered components. |
| `className`, `style` | | fills parent | Applied to the wrapping `<div>`. |

### `genuiLLM(options)`

Builds the transport object, for when you compose OpenUI chat components yourself.

```ts
import { genuiLLM } from "genui-react";

const llm = genuiLLM({ url: "/api/chat", headers: { Authorization: `Bearer ${token}` }, format: "ag-ui" });
```

Options: `url`, `headers?`, `body?`, `format?: "ag-ui" | "openai"`, `fetch?`.

### `<GenUIRenderer />`

Renders one OpenUI Lang response, e.g. a message you saved earlier.

```tsx
import { GenUIRenderer } from "genui-react";

<GenUIRenderer response={'root = TextContent("Hello")'} onAction={(e) => console.log(e)} />;
```

Props: `response: string | null`, `library?`, `onAction?`, `isStreaming?`, `initialState?`, `onStateUpdate?`, `tools?`, `onError?`, `loader?`.

### Other exports

- `defaultLibrary`, `chatLibrary`, `defaultPromptOptions`, `chatPromptOptions`: the built-in component libraries and their prompt options.
- `createLibrary`, `defineComponent`, `defineAction`: build your own component library.
- `buildMessage`, `parseMessage`: write and read stored OpenUI messages.
- `localStorageChat(llm, key)`, `restStorage({ baseUrl })`: thread storage helpers.
- `ThemeProvider`, `createTheme`: theming.
- Types: `GenUIChatProps`, `GenUIRendererProps`, `GenUILLMOptions`, `GenUILLM`, `GenUIFormat`, `GenUILibrary`, `GenUIActionEvent`, `GenUITheme`, `GenUIThemeProps`, `GenUIStarter`, `GenUIStorage`, `GenUIMessage`, `GenUIThread`, `GenUIComponentProps`, `GenUIPromptOptions`, `GenUIRestStorageOptions`.

Import from `genui-react`, not from `@openuidev/*` directly. The internals may change in later versions.

## Security

- **Safe links.** While mounted, `GenUIChat` routes `window.open` through `safeUrl()`: `@OpenUrl` links from the model open only for `http(s)`, `mailto`, `tel` and relative URLs, always with `noopener,noreferrer`. OpenUI's chat opens links without these checks. Turn this off with `safeLinks={false}`. With `GenUIRenderer`, `@OpenUrl` reaches your `onAction`: open it with `safeOpenUrl(event.params?.url)`.
- **Stored history.** `localStorageChat` stores threads as plain text that any script on your origin can read. Call `clearChatHistory(storageKey)` on logout. For sensitive data, use `storageKey={false}` or your own `storage`.
- **Dependency advisories.** OpenUI's dependencies pull in an old `katex` (GHSA-238p-pmpm-9mq7). Fix it with an npm override in your app's `package.json` (overrides only apply in apps, not libraries):

  ```json
  "overrides": { "katex": "^0.19.1" }
  ```

  They also pull in `zod` 3.x through `@ag-ui/core` (GHSA-mrhx-c7xc-m3w5, memory exhaustion on oversized input). Here zod only validates the SSE events your own backend sends, so exploiting it needs control of your server's stream. Don't override it to zod 4: the app still runs, but `@ag-ui/core`'s types turn into `unknown`. The fix has to come from an OpenUI release on `@ag-ui/core` 1.x.

## Dev tools

OpenUI's renderer normally adds its "OpenUI Inspect" widget in development. genui-react keeps it off. To turn it on, set `globalThis.GENUI_OPENUI_DEVTOOLS = true` before importing `genui-react`.

## Telemetry

genui-react sends nothing anywhere. One of its dependencies, `@openuidev/lang-core`, sends an anonymous install event from its `postinstall` script. To turn that off, install with:

```bash
OPENUI_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 npm install genui-react
```

## License

MIT. Copyright (c) 2026 Aditya Kumar Singh. OpenUI packages are MIT-licensed by their authors.
