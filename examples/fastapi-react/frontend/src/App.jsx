import "@openuidev/react-ui/styles/index.css";

import { AgentInterface, agUIAdapter, fetchLLM } from "@openuidev/react-ui";
import { openuiLibrary } from "@openuidev/react-ui/genui-lib";
import { localStorageChat } from "./lib/local-storage";

// The Python backend (genui) streams AG-UI events; nothing here talks to any cloud.
const { llm, storage } = localStorageChat(
  fetchLLM({ url: "/api/chat", streamAdapter: agUIAdapter() }),
  "genui-example",
);

export default function App() {
  return (
    <div className="h-screen w-screen overflow-hidden">
      <AgentInterface llm={llm} storage={storage} componentLibrary={openuiLibrary} agentName="genui demo" />
    </div>
  );
}
