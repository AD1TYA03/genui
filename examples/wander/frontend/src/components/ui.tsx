import {
  ACTION_STEPS,
  FormValidationContext,
  action,
  defineComponent,
  useCreateFormValidation,
  useFormValidation,
  useIsStreaming,
  useTriggerAction,
} from "@openuidev/react-lang";
import { motion } from "motion/react";
import { Fragment, useState, type ReactNode } from "react";
import { z } from "zod/v4";
import { cx, useChatBridge } from "./bridge";
import { IconAlert, IconArrowRight, IconCheckCircle, IconInfo } from "./icons";
import { Swash } from "./sketches";

export const fadeUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const },
};

/** Tiny inline formatter: **bold** and *italic*. */
export function RichText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**") && p.length > 4)
          return (
            <strong key={i} className="font-semibold text-ink">
              {p.slice(2, -2)}
            </strong>
          );
        if (p.startsWith("*") && p.endsWith("*") && p.length > 2)
          return (
            <em key={i} className="font-display text-[1.05em] italic text-terracotta">
              {p.slice(1, -1)}
            </em>
          );
        return <Fragment key={i}>{p}</Fragment>;
      })}
    </>
  );
}

/* --------------------------------- Stack --------------------------------- */
const gapMap = { sm: "gap-3", md: "gap-5", lg: "gap-8" } as const;

export const Stack = defineComponent({
  name: "Stack",
  description:
    "Root layout container. Every response starts with root = Stack([...]). Stacks children vertically (default) or in a wrapping row.",
  props: z.object({
    children: z.array(z.any()).describe("Child components, rendered in order"),
    direction: z.enum(["column", "row"]).optional().describe('Layout direction, default "column"'),
    gap: z.enum(["sm", "md", "lg"]).optional().describe('Spacing between children, default "md"'),
  }),
  component: ({ props, renderNode }) => {
    const dir = props.direction ?? "column";
    return (
      <div
        className={cx(
          "flex min-w-0",
          dir === "row" ? "flex-row flex-wrap items-center" : "flex-col",
          gapMap[props.gap ?? "md"],
        )}
      >
        {renderNode(props.children)}
      </div>
    );
  },
});

/* -------------------------------- Heading -------------------------------- */
export const Heading = defineComponent({
  name: "Heading",
  description: "Elegant serif section heading with an optional one-line subtitle. Use to open a response or a section.",
  props: z.object({
    text: z.string().describe("Heading text, short and evocative (max ~8 words)"),
    subtitle: z.string().optional().describe("Optional supporting line under the heading"),
  }),
  component: ({ props }) => (
    <motion.div {...fadeUp} className="min-w-0">
      <h2 className="font-display text-[31px] font-normal leading-[1.08] tracking-[-0.02em] text-ink text-balance sm:text-[40px]">
        {props.text}
      </h2>
      <Swash className="mt-1.5 text-mustard" />
      {props.subtitle ? (
        <p className="mt-2 max-w-[60ch] font-hand text-[22px] leading-snug text-ink-2 text-pretty">{props.subtitle}</p>
      ) : null}
    </motion.div>
  ),
});

/* ---------------------------------- Text --------------------------------- */
export const Text = defineComponent({
  name: "Text",
  description: "A paragraph of body copy. Supports **bold** and *italic*. Keep it warm, concise and specific.",
  props: z.object({
    content: z.string().describe("Paragraph text"),
    tone: z.enum(["default", "muted"]).optional().describe('"muted" for secondary notes, default "default"'),
  }),
  component: ({ props }) => (
    <motion.p
      {...fadeUp}
      className={cx(
        "max-w-[68ch] whitespace-pre-line text-pretty leading-relaxed",
        props.tone === "muted" ? "text-[14px] text-ink-3" : "text-[16.5px] text-ink-2",
      )}
    >
      <RichText text={props.content ?? ""} />
    </motion.p>
  ),
});

/* --------------------------------- Button -------------------------------- */
export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cx("inline-block size-4 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

export const buttonClasses = {
  base: "group/btn relative inline-flex select-none items-center justify-center gap-2 rounded-full font-medium transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-teal/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-50",
  primary:
    "h-12 px-6 text-[15px] text-surface bg-ink border-[1.5px] border-ink shadow-[3px_3px_0_var(--terracotta)] hover:-translate-y-px hover:shadow-[4px_5px_0_var(--terracotta)] active:translate-y-px active:shadow-[1px_1px_0_var(--terracotta)]",
  secondary:
    "h-12 px-6 text-[15px] text-ink border-[1.5px] border-ink/70 bg-surface shadow-[3px_3px_0_color-mix(in_oklab,var(--ink)_25%,transparent)] hover:-translate-y-px hover:bg-[#fffdf8] active:translate-y-px active:shadow-none",
  ghost: "h-10 px-3 text-[14px] text-ink-2 underline decoration-ink/30 decoration-wavy underline-offset-4 hover:text-ink hover:decoration-terracotta",
};

export const Button = defineComponent({
  name: "Button",
  description:
    'Pill button. Give it an action such as @ToAssistant("Check availability") — the current form state ($bindings) is sent along with the message. Without an action it sends its label.',
  props: z.object({
    label: z.string().describe("Short call to action, e.g. \"Check availability\""),
    action: action().optional().describe("What happens on click, usually @ToAssistant(message, context?)"),
    variant: z
      .enum(["primary", "secondary", "ghost"])
      .optional()
      .describe('"primary" (one per view, the main next step), "secondary", or "ghost"; default "primary"'),
  }),
  component: ({ props }) => {
    const triggerAction = useTriggerAction();
    const isStreaming = useIsStreaming();
    const formValidation = useFormValidation();
    const bridge = useChatBridge();
    const [clicked, setClicked] = useState(false);
    const variant = props.variant ?? "primary";
    const label = props.label ?? "";
    return (
      <button
        type="button"
        disabled={isStreaming || !label}
        className={cx(buttonClasses.base, buttonClasses[variant])}
        onClick={() => {
          const act = props.action as { steps?: { type: string }[] } | undefined;
          if (formValidation && variant === "primary") {
            const needs =
              !act?.steps || act.steps.some((s) => s.type === ACTION_STEPS.ToAssistant || s.type === "custom_action");
            if (needs && !formValidation.validateForm()) return;
          }
          setClicked(true);
          window.setTimeout(() => setClicked(false), 1600);
          void triggerAction(label, undefined, props.action as never);
        }}
      >
        {clicked && bridge?.busy ? <Spinner /> : null}
        <span>{label}</span>
        {variant === "primary" ? (
          <IconArrowRight size={16} className="transition-transform duration-300 group-hover/btn:translate-x-0.5" />
        ) : null}
      </button>
    );
  },
});

/* ------------------------------ Suggestions ------------------------------ */
const TAG_TINTS = ["#ecd9b4", "#d8e6df", "#f2dccf", "#dfe7ee"];

export function SuggestionChips({
  items,
  onPick,
  disabled,
  className,
}: {
  items: string[];
  onPick: (s: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <div className={cx("flex flex-wrap gap-x-3 gap-y-2.5", className)}>
      {items.map((s, i) => (
        <motion.button
          key={s + i}
          type="button"
          disabled={disabled}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 * i, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          onClick={() => onPick(s)}
          className="group/chip relative rounded-[4px] outline-none transition-transform duration-300 hover:-translate-y-0.5 hover:-rotate-2 focus-visible:ring-2 focus-visible:ring-teal/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:pointer-events-none disabled:opacity-50"
          style={{ filter: "drop-shadow(0 1px 0.5px rgba(60,40,10,0.22))" }}
        >
          <span
            className="tag-chip relative flex items-center gap-2.5 py-2 pl-[22px] pr-4 text-[14px] font-medium text-ink"
            style={{ background: TAG_TINTS[i % TAG_TINTS.length] }}
          >
            <span aria-hidden className="size-[7px] shrink-0 rounded-full bg-bg ring-[1.5px] ring-ink/45" />
            {s}
          </span>
        </motion.button>
      ))}
    </div>
  );
}

export const Suggestions = defineComponent({
  name: "Suggestions",
  description:
    "Tappable follow-up chips shown at the end of a response; tapping one sends its text as the user's next message. 2-4 short items.",
  props: z.object({
    items: z.array(z.string()).describe('Short follow-ups in the user\'s voice, e.g. "Something under ₹15k a night"'),
  }),
  component: ({ props }) => {
    const bridge = useChatBridge();
    const triggerAction = useTriggerAction();
    const isStreaming = useIsStreaming();
    const items = (props.items ?? []).filter((s): s is string => typeof s === "string" && s.length > 0);
    if (!items.length) return null;
    return (
      <SuggestionChips
        items={items}
        disabled={isStreaming || bridge?.busy}
        onPick={(s) => (bridge ? bridge.send(s) : void triggerAction(s))}
      />
    );
  },
});

/* -------------------------------- Callout -------------------------------- */
const calloutTone = {
  info: { icon: IconInfo, paper: "#dfecea", tape: "var(--sky)", fg: "text-teal", tilt: -0.7 },
  success: { icon: IconCheckCircle, paper: "#f7e9ad", tape: "var(--sage)", fg: "text-sage", tilt: 0.6 },
  warning: { icon: IconAlert, paper: "#f6dccf", tape: "var(--terracotta)", fg: "text-terracotta", tilt: -0.5 },
} as const;

export const Callout = defineComponent({
  name: "Callout",
  description: "A highlighted note: tips, policies, confirmations or warnings (e.g. dates unavailable).",
  props: z.object({
    title: z.string().describe("Short bold title"),
    body: z.string().describe("One or two sentences"),
    tone: z.enum(["info", "success", "warning"]).optional().describe('Default "info"'),
  }),
  component: ({ props }) => {
    const t = calloutTone[props.tone ?? "info"] ?? calloutTone.info;
    const Icon = t.icon;
    return (
      <motion.div
        initial={{ opacity: 0, y: 12, rotate: 0 }}
        animate={{ opacity: 1, y: 0, rotate: t.tilt }}
        transition={fadeUp.transition}
        role={props.tone === "warning" ? "alert" : "note"}
        className="relative w-full max-w-[560px] rounded-[2px] px-5 pb-5 pt-6 shadow-[0_1px_1px_rgba(60,40,10,0.1),0_14px_18px_-14px_rgba(60,40,10,0.45)] sm:px-6"
        style={{ background: t.paper }}
      >
        <span className="tape -top-2.5 left-1/2 w-20 -translate-x-1/2 rotate-2" style={{ ["--tape" as string]: t.tape }} />
        <div className="flex gap-3">
          <Icon size={20} className={cx("mt-1 shrink-0", t.fg)} />
          <div className="min-w-0">
            <p className="font-hand text-[25px] font-semibold leading-[1.05] text-ink">{props.title}</p>
            <p className="mt-1.5 text-[14.5px] leading-relaxed text-ink-2 text-pretty">
              <RichText text={props.body ?? ""} />
            </p>
          </div>
        </div>
      </motion.div>
    );
  },
});

/* ---------------------------------- Form --------------------------------- */
function FormShell({ children }: { children: ReactNode }) {
  const validation = useCreateFormValidation();
  // No FormNameContext on purpose: actions then carry the page's $variables
  // (checkIn/checkOut/adults/children) in formState as plain values.
  return (
    <FormValidationContext.Provider value={validation}>
      <motion.div
        {...fadeUp}
        role="form"
        className="paper-card relative flex flex-col gap-7 rounded-[6px] p-5 outline-[1.5px] outline-dashed outline-offset-[-9px] outline-ink/15 sm:p-8 [&>button]:self-stretch sm:[&>button]:self-start"
      >
        {children}
      </motion.div>
    </FormValidationContext.Provider>
  );
}

export const Form = defineComponent({
  name: "Form",
  description:
    'Groups booking inputs (DateRangePicker, GuestPicker) with one submit Button whose action is @ToAssistant(...). The bound $variables reach the agent with the message.',
  props: z.object({
    children: z.array(z.any()).describe("Pickers followed by the submit Button"),
  }),
  component: ({ props, renderNode }) => <FormShell>{renderNode(props.children)}</FormShell>,
});
