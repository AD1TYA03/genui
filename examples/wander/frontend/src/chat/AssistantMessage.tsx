import type { AssistantMessage as AGAssistantMessage } from "@openuidev/react-headless";
import { useThread } from "@openuidev/react-headless";
import { BuiltinActionType, Renderer, buildMessage, type ActionEvent, type OpenUIError } from "@openuidev/react-lang";
import { memo, useCallback, useMemo } from "react";
import { library } from "../library";
import { buildActionUserMessage, readMessage, textOf } from "./messages";

/** Renders one assistant message's OpenUI Lang through the real Renderer. */
export const AssistantMessage = memo(function AssistantMessage({
  message,
  isStreaming,
}: {
  message: AGAssistantMessage;
  isStreaming: boolean;
}) {
  const processMessage = useThread((s) => s.processMessage);
  const updateMessage = useThread((s) => s.updateMessage);
  const raw = textOf(message.content);
  const { content, context } = useMemo(() => readMessage(raw, isStreaming), [raw, isStreaming]);

  // Form state persisted on the message (see handleStateUpdate) hydrates the Renderer.
  const initialState = useMemo(() => {
    if (Array.isArray(context) && context[0] && typeof context[0] === "object") return context[0] as Record<string, unknown>;
    if (context && typeof context === "object" && !Array.isArray(context)) return context as Record<string, unknown>;
    return undefined;
  }, [context]);

  const handleStateUpdate = useCallback(
    (state: Record<string, unknown>) => {
      if (isStreaming) return;
      const hasState = Object.keys(state).length > 0;
      updateMessage({
        ...message,
        content: buildMessage({ content: content ?? "", context: hasState ? [state] : undefined }),
      });
    },
    [updateMessage, message, content, isStreaming],
  );

  const handleAction = useCallback(
    (event: ActionEvent) => {
      if (event.type === BuiltinActionType.ContinueConversation) {
        void processMessage({ role: "user", content: buildActionUserMessage(event) });
      } else if (event.type === BuiltinActionType.OpenUrl) {
        const url = event.params?.["url"];
        if (typeof url === "string") window.open(url, "_blank", "noopener");
      }
    },
    [processMessage],
  );

  const handleError = useCallback((errors: OpenUIError[]) => {
    if (errors.length && import.meta.env.DEV) console.debug("[wander] OpenUI errors", errors);
  }, []);

  if (!content?.trim()) return null;
  return (
    <Renderer
      response={content}
      library={library}
      isStreaming={isStreaming}
      onAction={handleAction}
      onStateUpdate={handleStateUpdate}
      initialState={initialState}
      onError={handleError}
      queryLoader={null}
    />
  );
});
