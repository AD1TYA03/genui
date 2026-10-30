import { useEffect } from "react";

export function useTitle(page?: string) {
  useEffect(() => {
    document.title = page ? `${page} · genui` : "genui · Generative UI for Python agents";
  }, [page]);
}
