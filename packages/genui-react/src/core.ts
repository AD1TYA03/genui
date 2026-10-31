// genui-react/core: the renderer, transport and storage WITHOUT OpenUI's default component
// library (@openuidev/react-ui). Use it when you render your own components: the bundle is a
// fraction of the size. `GenUIChat` and `defaultLibrary` live in the main entry.

export { GenUIRenderer, type GenUIRendererProps } from "./RendererCore";
export { genuiLLM, type GenUIFormat, type GenUILLM, type GenUILLMOptions } from "./llm";
export { clearChatHistory, localStorageChat } from "./storage";
export { guardWindowOpen, safeOpenUrl, safeUrl } from "./safeUrl";
export type { GenUIActionEvent, GenUILibrary } from "./coreTypes";

// Building component libraries and stored messages.
export {
  createLibrary,
  defineComponent,
  defineAction,
  buildMessage,
  parseMessage,
  type ComponentRenderProps as GenUIComponentProps,
  type PromptOptions as GenUIPromptOptions,
} from "@openuidev/react-lang";

// Chat state, transport and storage building blocks (headless: bring your own UI).
export {
  ChatProvider,
  useThread,
  useThreadList,
  restStorage,
  type ChatStorage as GenUIStorage,
  type Message as GenUIMessage,
  type Thread as GenUIThread,
  type RestStorageOptions as GenUIRestStorageOptions,
} from "@openuidev/react-headless";
