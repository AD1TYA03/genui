import { openuiLibrary } from "@openuidev/react-ui";
import { GenUIRenderer as CoreRenderer, type GenUIRendererProps as CoreProps } from "./RendererCore";

export interface GenUIRendererProps extends Omit<CoreProps, "library"> {
  /** Component library to render with. Defaults to OpenUI's default library. */
  library?: CoreProps["library"];
}

/** Render a single OpenUI Lang response, e.g. a stored assistant message. */
export function GenUIRenderer({ library, ...props }: GenUIRendererProps) {
  return <CoreRenderer library={library ?? openuiLibrary} {...props} />;
}
