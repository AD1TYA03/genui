import { ChatProvider, agUIAdapter, fetchLLM, useThread } from "@openuidev/react-headless";
import { useEffect, useMemo } from "react";
import { Shell } from "./chat/Shell";

const params = new URLSearchParams(window.location.search);
const DEMO = import.meta.env.DEV ? params.get("demo") : null;

function DemoSeeder() {
  const setMessages = useThread((s) => s.setMessages);
  useEffect(() => {
    if (DEMO === "1") {
      void import("./chat/demo").then((m) => setMessages(m.demoConversation()));
    }
  }, [setMessages]);
  return null;
}

export default function App() {
  const llm = useMemo(() => {
    // The Python backend (genui) streams AG-UI events from POST /api/chat.
    return fetchLLM({ url: "/api/chat", streamAdapter: agUIAdapter() });
  }, []);
  const demoLLM = useDemoLLM();
  return (
    <ChatProvider llm={demoLLM ?? llm}>
      {DEMO && <DemoSeeder />}
      <Shell demo={!!DEMO} />
    </ChatProvider>
  );
}

let demoLLMInstance: import("@openuidev/react-headless").ChatLLM | null = null;
function useDemoLLM() {
  return DEMO ? demoLLMInstance : null;
}

/** Load the dev-only demo module before first render so the fake LLM is ready. */
export async function prepareDemo() {
  if (!DEMO) return;
  const m = await import("./chat/demo");
  demoLLMInstance = m.demoLLM();
}
