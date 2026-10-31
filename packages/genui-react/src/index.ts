// genui-react: React companion for genui-py.
// Built on OpenUI's MIT-licensed renderer (@openuidev/*). Depend on this
// package's exports, not on @openuidev directly; internals may change.

// OpenUI's dev-only Inspect widget is switched off by dist/devtools.js, which the build
// prepends as the first import of dist/index.js (see tsup.config.ts).

export { GenUIChat, type GenUIChatProps } from "./GenUIChat";
export { GenUIRenderer, type GenUIRendererProps } from "./GenUIRenderer";
export { genuiLLM, type GenUIFormat, type GenUILLM, type GenUILLMOptions } from "./llm";
export { clearChatHistory, localStorageChat } from "./storage";
export { safeOpenUrl, safeUrl } from "./safeUrl";
export type { GenUIActionEvent, GenUILibrary, GenUIStarter, GenUITheme, GenUIThemeProps } from "./types";

// Component libraries and prompt options.
export {
  openuiLibrary as defaultLibrary,
  openuiChatLibrary as chatLibrary,
  openuiPromptOptions as defaultPromptOptions,
  openuiChatPromptOptions as chatPromptOptions,
  createTheme,
  ThemeProvider,
} from "@openuidev/react-ui";

// Building custom component libraries and stored messages.
export {
  createLibrary,
  defineComponent,
  defineAction,
  buildMessage,
  parseMessage,
  type ComponentRenderProps as GenUIComponentProps,
  type PromptOptions as GenUIPromptOptions,
} from "@openuidev/react-lang";

// Transport and storage building blocks.
export {
  restStorage,
  type ChatStorage as GenUIStorage,
  type Message as GenUIMessage,
  type Thread as GenUIThread,
  type RestStorageOptions as GenUIRestStorageOptions,
} from "@openuidev/react-headless";
