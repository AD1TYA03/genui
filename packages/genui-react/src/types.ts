import type { ConversationStarterProps, ThemeProps } from "@openuidev/react-ui";
import type { ActionEvent, Library } from "@openuidev/react-lang";

/** A component library that tells the model which components it may render. */
export type GenUILibrary = Library;

/** Event emitted when a rendered component triggers an action (button click, form submit, ...). */
export type GenUIActionEvent = ActionEvent;

/** Full theme configuration (mode, light/dark overrides, CSS scope). */
export type GenUIThemeProps = Omit<ThemeProps, "children">;

/** Theme shorthand: `"light"`, `"dark"`, or full theme props. */
export type GenUITheme = "light" | "dark" | GenUIThemeProps;

/** A conversation starter shown on the welcome screen. */
export type GenUIStarter = ConversationStarterProps;
