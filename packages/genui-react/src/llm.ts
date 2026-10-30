import {
  agUIAdapter,
  fetchLLM,
  openAIAdapter,
  openAIMessageFormat,
  type ChatLLM,
} from "@openuidev/react-headless";

/** Wire format spoken by the backend endpoint. */
export type GenUIFormat = "ag-ui" | "openai";

export interface GenUILLMOptions {
  /** POST endpoint that streams the reply, e.g. `"/api/chat"`. */
  url: string;
  /** Extra request headers (auth tokens, etc.). */
  headers?: Record<string, string>;
  /** Extra fields merged into the JSON request body. */
  body?: Record<string, unknown>;
  /**
   * `"ag-ui"` (default): AG-UI SSE events, as streamed by genui-py.
   * `"openai"`: OpenAI Chat Completions SSE chunks with OpenAI-shaped messages.
   */
  format?: GenUIFormat;
  /** Custom fetch implementation (tests, auth wrappers). */
  fetch?: typeof fetch;
}

/** The LLM transport object consumed by `<GenUIChat llm>` and OpenUI chat components. */
export type GenUILLM = ChatLLM;

/**
 * Build the LLM transport for a genui backend.
 *
 * The request body is `{ threadId, runId, messages, tools, context, ...body }`,
 * POSTed as JSON to `url`; the response is parsed as a stream in `format`.
 */
export function genuiLLM({ url, headers, body, format = "ag-ui", fetch }: GenUILLMOptions): GenUILLM {
  if (format === "openai") {
    return fetchLLM({
      url,
      headers,
      body,
      fetch,
      streamAdapter: openAIAdapter(),
      messageFormat: openAIMessageFormat,
    });
  }
  if (format !== "ag-ui") {
    throw new Error(`genui-react: unknown format "${String(format)}" (expected "ag-ui" or "openai")`);
  }
  return fetchLLM({ url, headers, body, fetch, streamAdapter: agUIAdapter() });
}
