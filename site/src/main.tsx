import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./index.css";
import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Layout } from "./components/Layout";
import Home from "./pages/Home";

const Playground = lazy(() => import("./pages/Playground"));
const Wander = lazy(() => import("./pages/Wander"));
const NotFound = lazy(() => import("./pages/NotFound"));

function PageFallback() {
  return <div className="min-h-[60vh]" />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="gallery" element={<Navigate to="/wander" replace />} />
            <Route path="playground" element={<Playground />} />
            <Route path="wander" element={<Wander />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
);
