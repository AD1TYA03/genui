import "./devtools-flag";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App, { prepareDemo } from "./App";
import "./index.css";

void prepareDemo().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
