import type { ActionEvent, Library } from "@openuidev/react-lang";

/** A component library that tells the model which components it may render. */
export type GenUILibrary = Library;

/** Event emitted when a rendered component triggers an action (button click, form submit, ...). */
export type GenUIActionEvent = ActionEvent;
