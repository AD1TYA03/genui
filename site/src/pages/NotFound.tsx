import { Link } from "react-router";
import { useTitle } from "../lib/useTitle";

export default function NotFound() {
  useTitle("Not found");
  return (
    <div className="mx-auto max-w-xl px-5 py-32 text-center">
      <p className="font-mono text-6xl font-semibold text-dim">404</p>
      <h1 className="mt-4 text-2xl font-semibold">This page didn&rsquo;t render.</h1>
      <p className="mt-2 text-muted">Even the best agents hallucinate a route now and then.</p>
      <Link to="/" className="mt-8 inline-flex h-11 items-center rounded-xl bg-fg px-5 text-sm font-semibold text-ink">
        Back home
      </Link>
    </div>
  );
}
