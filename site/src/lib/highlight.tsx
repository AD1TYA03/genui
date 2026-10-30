import { Fragment, type ReactNode } from "react";

export type Lang = "oui" | "python" | "tsx" | "bash";

type Rule = [RegExp, string | ((m: RegExpExecArray, src: string, end: number) => string)];

const nextNonSpace = (src: string, i: number) => {
  while (i < src.length && (src[i] === " " || src[i] === "\t")) i++;
  return src[i];
};

const RULES: Record<Lang, Rule[]> = {
  oui: [
    [/\/\/[^\n]*/y, "comment"],
    [/"(?:[^"\\\n]|\\.)*"?/y, "string"],
    [/-?\d+(?:\.\d+)?/y, "number"],
    [/@[A-Za-z_]\w*/y, "action"],
    [/\$[A-Za-z_]\w*/y, "var"],
    [/\b(?:true|false|null)\b/y, "keyword"],
    [
      /[A-Za-z_]\w*/y,
      (m, src, end) => {
        if (m[0] === "root") return "root";
        if (/^[A-Z]/.test(m[0]) && nextNonSpace(src, end) === "(") return "component";
        return "ident";
      },
    ],
    [/[()[\]{},:=]/y, "punct"],
  ],
  python: [
    [/#[^\n]*/y, "comment"],
    [/[rbfu]{0,2}("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')/y, "string"],
    [/@[A-Za-z_][\w.]*/y, "action"],
    [/\d+(?:\.\d+)?/y, "number"],
    [
      /\b(?:from|import|as|def|async|await|return|class|if|else|elif|for|in|with|yield|None|True|False|and|or|not|lambda|try|except|raise)\b/y,
      "keyword",
    ],
    [/[A-Za-z_]\w*/y, (_m, src, end) => (nextNonSpace(src, end) === "(" ? "fn" : "ident")],
    [/[()[\]{},:=.*]/y, "punct"],
  ],
  tsx: [
    [/\/\/[^\n]*/y, "comment"],
    [/"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`/y, "string"],
    [/<\/?[A-Za-z][\w.]*/y, "tag"],
    [/\/?>/y, "tag"],
    [/\d+(?:\.\d+)?/y, "number"],
    [
      /\b(?:import|from|export|default|function|return|const|let|await|async|new|type|interface)\b/y,
      "keyword",
    ],
    [
      /[A-Za-z_]\w*/y,
      (_m, src, end) => {
        const n = nextNonSpace(src, end);
        // JSX attribute: name immediately followed by "=" (no spaces), not "==" / "=>".
        if (src[end] === "=" && src[end + 1] !== "=" && src[end + 1] !== ">") return "attr";
        if (n === "(") return "fn";
        return "ident";
      },
    ],
    [/[()[\]{},:=.;]/y, "punct"],
  ],
  bash: [
    [/#[^\n]*/y, "comment"],
    [/"(?:[^"\\\n]|\\.)*"|'[^'\n]*'/y, "string"],
    [/\b(?:pip|npm|npx|uv|cd)\b/y, "keyword"],
    [/--?[\w-]+/y, "attr"],
  ],
};

export interface Token {
  cls: string | null;
  text: string;
}

export function tokenize(src: string, lang: Lang): Token[] {
  const rules = RULES[lang];
  const out: Token[] = [];
  let plain = "";
  let i = 0;
  outer: while (i < src.length) {
    for (const [re, cls] of rules) {
      re.lastIndex = i;
      const m = re.exec(src);
      if (m && m[0].length > 0) {
        if (plain) {
          out.push({ cls: null, text: plain });
          plain = "";
        }
        const end = i + m[0].length;
        out.push({ cls: typeof cls === "function" ? cls(m, src, end) : cls, text: m[0] });
        i = end;
        continue outer;
      }
    }
    plain += src[i];
    i++;
  }
  if (plain) out.push({ cls: null, text: plain });
  return out;
}

export function Highlight({ code, lang }: { code: string; lang: Lang }): ReactNode {
  return (
    <>
      {tokenize(code, lang).map((t, i) =>
        t.cls ? (
          <span key={i} className={`tok-${t.cls}`}>
            {t.text}
          </span>
        ) : (
          <Fragment key={i}>{t.text}</Fragment>
        ),
      )}
    </>
  );
}
