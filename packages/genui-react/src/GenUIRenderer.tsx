import type { ReactNode } from "react";
import { Renderer } from "@openuidev/react-lang";
import { openuiLibrary } from "@openuidev/react-ui";
import type { GenUIActionEvent, GenUILibrary } from "./types";

export interface GenUIRendererProps {
  /** An OpenUI Lang program, or a full stored message with `]]>openui:` markers. */
  response: string | null;
  /** Component library to render with. Defaults to OpenUI's default library. */
  library?: GenUILibrary;
  /** Receives actions triggered by rendered components. */
  onAction?: (event: GenUIActionEvent) => void;
  /** Set while the response is still streaming in (disables form interaction). */
  isStreaming?: boolean;
  /** Form/state values to hydrate, e.g. saved from a previous `onStateUpdate`. */
  initialState?: Record<string, unknown>;
  /** Called whenever form field values change. */
  onStateUpdate?: (state: Record<string, unknown>) => void;
  /** Handlers for `Query()` / `Mutation()` calls: `{ tool_name: async (args) => result }`. */
  tools?: Record<string, (args: Record<string, unknown>) => Promise<unknown>>;
  /** Called with parser / runtime errors (`[]` once resolved). */
  onError?: (errors: unknown[]) => void;
  /** Custom loading indicator for pending queries. */
  loader?: ReactNode;
}

/** Render a single OpenUI Lang response, e.g. a stored assistant message. */
export function GenUIRenderer({
  response,
  library,
  onAction,
  isStreaming,
  initialState,
  onStateUpdate,
  tools,
  onError,
  loader,
}: GenUIRendererProps) {
  return (
    <Renderer
      response={response}
      library={library ?? openuiLibrary}
      onAction={onAction}
      isStreaming={isStreaming}
      initialState={initialState}
      onStateUpdate={onStateUpdate}
      toolProvider={tools}
      onError={onError}
      queryLoader={loader}
    />
  );
}
