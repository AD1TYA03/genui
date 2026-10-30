import "genui-react/styles.css";
import { Component, type ReactNode } from "react";
import { GenUIRenderer, ThemeProvider, type GenUIActionEvent } from "genui-react";

/** Brand-tuned dark theme for OpenUI's default component library. */
const darkTheme = {
  background: "#0b0b14",
  foreground: "#13131f",
  popoverBackground: "#191927",
  fontBody: '"Inter Variable", ui-sans-serif, system-ui, sans-serif',
  fontHeading: '"Inter Variable", ui-sans-serif, system-ui, sans-serif',
  fontLabel: '"Inter Variable", ui-sans-serif, system-ui, sans-serif',
  fontNumbers: '"Inter Variable", ui-sans-serif, system-ui, sans-serif',
  fontCode: '"JetBrains Mono Variable", ui-monospace, monospace',
  textBrand: "#a78bfa",
  borderAccentSelected: "#8b5cf6",
  interactiveAccentDefault: "#7c3aed",
  interactiveAccentHover: "#8b5cf6",
  interactiveAccentPressed: "#6d28d9",
  interactiveAccentDisabled: "rgba(124, 58, 237, 0.4)",
  textAccentPrimary: "#ffffff",
};

class Boundary extends Component<{ children: ReactNode; resetKey: string }, { error: Error | null; key: string }> {
  state = { error: null as Error | null, key: this.props.resetKey };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  static getDerivedStateFromProps(props: { resetKey: string }, state: { key: string; error: Error | null }) {
    if (props.resetKey !== state.key) return { key: props.resetKey, error: null };
    return null;
  }
  render() {
    if (this.state.error) {
      return (
        <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-4 font-mono text-sm text-red-200">
          Render error: {this.state.error.message}
        </div>
      );
    }
    return this.props.children;
  }
}

export interface GenUIFrameProps {
  response: string | null;
  isStreaming?: boolean;
  onAction?: (event: GenUIActionEvent) => void;
  onError?: (errors: unknown[]) => void;
}

export default function GenUIFrame({ response, isStreaming, onAction, onError }: GenUIFrameProps) {
  return (
    <ThemeProvider mode="dark" darkTheme={darkTheme}>
      <div className="genui-frame">
        <Boundary resetKey={response ?? ""}>
          <GenUIRenderer response={response} isStreaming={isStreaming} onAction={onAction} onError={onError} />
        </Boundary>
      </div>
    </ThemeProvider>
  );
}
