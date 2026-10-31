import { useEffect, useMemo, type CSSProperties, type ReactNode } from "react";
import { AgentInterface, openuiLibrary, type AgentInterfaceProps } from "@openuidev/react-ui";
import type { ChatStorage } from "@openuidev/react-headless";
import { genuiLLM, type GenUIFormat, type GenUILLM } from "./llm";
import { guardWindowOpen } from "./safeUrl";
import { localStorageChat } from "./storage";
import type { GenUIActionEvent, GenUILibrary, GenUIStarter, GenUITheme, GenUIThemeProps } from "./types";

export interface GenUIChatProps {
  /** POST endpoint of your genui backend. Defaults to `"/api/chat"`. */
  url?: string;
  /** Component library the model renders with. Defaults to OpenUI's default library (`defaultLibrary`). */
  library?: GenUILibrary;
  /** Display name shown in the chat chrome. */
  agentName?: string;
  /** Brand logo URL shown in the sidebar / mobile header. */
  logoUrl?: string;
  /** Extra request headers sent with every chat request. */
  headers?: Record<string, string>;
  /** Extra fields merged into every chat request body. */
  body?: Record<string, unknown>;
  /** Backend stream format. Defaults to `"ag-ui"` (what genui-py streams). */
  format?: GenUIFormat;
  /**
   * localStorage namespace for threads and messages. Defaults to `"genui"`.
   * Pass `false` to keep history in memory only (lost on reload).
   */
  storageKey?: string | false;
  /** Custom thread storage; overrides `storageKey`. */
  storage?: ChatStorage;
  /** Custom LLM transport; overrides `url`, `headers`, `body` and `format`. */
  llm?: GenUILLM;
  /** `"light"`, `"dark"`, or full theme props (`mode`, `lightTheme`, `darkTheme`, ...). */
  theme?: GenUITheme;
  /** Conversation starters shown on the welcome screen. */
  starters?: GenUIStarter[];
  /** Receives custom actions triggered by rendered components. */
  onAction?: (event: GenUIActionEvent) => void;
  /** Class name for the wrapping element. */
  className?: string;
  /** Inline style for the wrapping element (defaults to filling its parent). */
  style?: CSSProperties;
  /**
   * Check links the model opens with `@OpenUrl` (default `true`): only `http(s)`, `mailto`,
   * `tel` and relative URLs open, always with `noopener`. While mounted this wraps
   * `window.open` for the page, because OpenUI's chat opens links without these checks.
   */
  safeLinks?: boolean;
  /** Advanced: slot children forwarded to OpenUI's AgentInterface (Sidebar, Welcome, ...). */
  children?: ReactNode;
}

const fill: CSSProperties = { height: "100%", width: "100%" };

function normalizeTheme(theme: GenUITheme | undefined): GenUIThemeProps | undefined {
  if (theme === undefined) return undefined;
  return typeof theme === "string" ? { mode: theme } : theme;
}

/**
 * Full chat UI wired to a genui backend: streaming AG-UI transport, local
 * thread history, and generative UI rendering with OpenUI's default library.
 *
 * Remember to import the stylesheet once: `import "genui-react/styles.css"`.
 */
export function GenUIChat({
  url = "/api/chat",
  library,
  agentName,
  logoUrl,
  headers,
  body,
  format = "ag-ui",
  storageKey = "genui",
  storage,
  llm,
  theme,
  starters,
  onAction,
  className,
  style,
  safeLinks = true,
  children,
}: GenUIChatProps) {
  useEffect(() => (safeLinks ? guardWindowOpen() : undefined), [safeLinks]);

  // Object props are usually inline literals; key memoisation on their content.
  const headersKey = headers ? JSON.stringify(headers) : "";
  const bodyKey = body ? JSON.stringify(body) : "";

  const wired = useMemo(() => {
    const transport = llm ?? genuiLLM({ url, headers, body, format });
    if (storage) return { llm: transport, storage };
    if (storageKey === false) return { llm: transport, storage: undefined };
    return localStorageChat(transport, storageKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llm, url, headersKey, bodyKey, format, storage, storageKey]);

  const agentProps: AgentInterfaceProps = {
    llm: wired.llm,
    storage: wired.storage,
    componentLibrary: library ?? openuiLibrary,
    agentName,
    logoUrl,
    theme: normalizeTheme(theme),
    starters,
    onAction,
    children,
  };

  return (
    <div className={className} style={{ ...fill, ...style }} data-genui-chat="">
      <AgentInterface {...agentProps} />
    </div>
  );
}
