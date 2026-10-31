import type { ConversationStarterProps, ThemeProps } from "@openuidev/react-ui";

export type { GenUIActionEvent, GenUILibrary } from "./coreTypes";

/** Full theme configuration (mode, light/dark overrides, CSS scope). */
export type GenUIThemeProps = Omit<ThemeProps, "children">;

/** Theme shorthand: `"light"`, `"dark"`, or full theme props. */
export type GenUITheme = "light" | "dark" | GenUIThemeProps;

/** A conversation starter shown on the welcome screen. */
export type GenUIStarter = ConversationStarterProps;
