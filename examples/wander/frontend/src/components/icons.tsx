import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function make(paths: React.ReactNode, displayName: string) {
  const Icon = ({ size = 18, strokeWidth = 1.6, ...rest }: IconProps) => (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {paths}
    </svg>
  );
  Icon.displayName = displayName;
  return Icon;
}

export const IconStar = ({ size = 14, ...rest }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...rest}>
    <path d="M12 2.8l2.76 5.6 6.18.9-4.47 4.36 1.05 6.15L12 16.9l-5.52 2.91 1.05-6.15L3.06 9.3l6.18-.9L12 2.8z" />
  </svg>
);

export const IconPin = make(
  <>
    <path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z" />
    <circle cx="12" cy="9.5" r="2.5" />
  </>,
  "IconPin",
);
export const IconArrowRight = make(<path d="M5 12h14M13 6l6 6-6 6" />, "IconArrowRight");
export const IconArrowUp = make(<path d="M12 19V5M6 11l6-6 6 6" />, "IconArrowUp");
export const IconChevronLeft = make(<path d="M15 6l-6 6 6 6" />, "IconChevronLeft");
export const IconChevronRight = make(<path d="M9 6l6 6-6 6" />, "IconChevronRight");
export const IconMinus = make(<path d="M5 12h14" />, "IconMinus");
export const IconPlus = make(<path d="M12 5v14M5 12h14" />, "IconPlus");
export const IconSparkle = make(
  <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z" />,
  "IconSparkle",
);
export const IconInfo = make(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8h.01" />
  </>,
  "IconInfo",
);
export const IconCheck = make(<path d="M5 12.5l4.5 4.5L19 7.5" />, "IconCheck");
export const IconCheckCircle = make(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12.5l2.8 2.8L16 10" />
  </>,
  "IconCheckCircle",
);
export const IconAlert = make(
  <>
    <path d="M12 3.5L2.5 20h19L12 3.5z" />
    <path d="M12 10v4.5M12 17.5h.01" />
  </>,
  "IconAlert",
);
export const IconCalendar = make(
  <>
    <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
    <path d="M3.5 10h17M8 3v4M16 3v4" />
  </>,
  "IconCalendar",
);
export const IconUsers = make(
  <>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5" />
    <path d="M16 4.7a3.5 3.5 0 0 1 0 6.6M18 14.8c2 .7 3.2 2.4 3.5 5.2" />
  </>,
  "IconUsers",
);
export const IconMoon = make(<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />, "IconMoon");
export const IconSun = make(
  <>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4" />
  </>,
  "IconSun",
);
export const IconRefresh = make(
  <path d="M20 11a8 8 0 0 0-14.6-4.5L4 8M4 4v4h4M4 13a8 8 0 0 0 14.6 4.5L20 16M20 20v-4h-4" />,
  "IconRefresh",
);
export const IconStop = ({ size = 14, ...rest }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...rest}>
    <rect x="6" y="6" width="12" height="12" rx="2.5" />
  </svg>
);
export const IconPlane = make(
  <path d="M10.5 13.5L3 11l1.5-2 7.5 1.5 4.5-5c.8-.8 2.2-.9 3-.1.8.8.7 2.2-.1 3l-5 4.5L16 20.5l-2 1.5-2.5-7.5-3 3V20l-1.5 1-1-3.5L2.5 16l1-1.5H6l3-3" />,
  "IconPlane",
);
export const IconCompass = make(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M15.5 8.5l-2 5-5 2 2-5 5-2z" />
  </>,
  "IconCompass",
);

/* ----------------------------- amenity icons ----------------------------- */
const IconWifi = make(
  <path d="M2.5 9a14 14 0 0 1 19 0M5.5 12.5a9.5 9.5 0 0 1 13 0M8.8 15.8a4.8 4.8 0 0 1 6.4 0M12 19.2h.01" />,
  "IconWifi",
);
const IconPool = make(
  <path d="M2.5 17c1.6 0 1.6 1 3.2 1s1.6-1 3.2-1 1.6 1 3.1 1 1.6-1 3.2-1 1.6 1 3.2 1 1.6-1 3.1-1M8 15V6a2 2 0 0 1 4 0M16 15V6a2 2 0 0 0-4 0M8 9h8M8 12.5h8" />,
  "IconPool",
);
const IconCoffee = make(
  <>
    <path d="M4 9h12v5.5A5.5 5.5 0 0 1 10.5 20h-1A5.5 5.5 0 0 1 4 14.5V9z" />
    <path d="M16 10.5h1.5a2.5 2.5 0 0 1 0 5H16M8 3.5c-.6.8-.6 1.7 0 2.5M12 3.5c-.6.8-.6 1.7 0 2.5" />
  </>,
  "IconCoffee",
);
const IconFlame = make(
  <path d="M12 21c3.9 0 6.5-2.6 6.5-6.2 0-3.6-2.8-5.7-3.8-9.3-.5 2-1.6 3.1-2.9 3.6C11.8 6.4 10.6 4.4 8.5 3c.4 3.7-3 5.9-3 11.8C5.5 18.4 8.1 21 12 21z" />,
  "IconFlame",
);
const IconLeaf = make(
  <path d="M5 19c0-8 5-13.5 15-14-.2 9.8-5.5 15-13 15M5 19c2.5-4 5.5-6.5 9-8" />,
  "IconLeaf",
);
const IconMountain = make(<path d="M2.5 19.5l6.5-11 4 6.5 2.5-4 6 8.5h-19zM7.2 11.5l1.8 1.6 1.7-1.4" />, "IconMountain");
const IconCar = make(
  <>
    <path d="M4 16.5V12l2-5h12l2 5v4.5M4 16.5h16M4 16.5V19M20 16.5V19" />
    <circle cx="7.5" cy="13.5" r=".9" />
    <circle cx="16.5" cy="13.5" r=".9" />
  </>,
  "IconCar",
);
const IconUtensils = make(
  <path d="M6 3v7a2 2 0 0 0 2 2v9M10 3v7a2 2 0 0 1-2 2M8 3v5M17 21V3c-2.2 1.3-3 3.8-3 7v3h3" />,
  "IconUtensils",
);
const IconSnow = make(
  <path d="M12 2.5v19M4 7l16 10M4 17L20 7M9.5 4.5L12 6.5l2.5-2M9.5 19.5l2.5-2 2.5 2" />,
  "IconSnow",
);
const IconWaves = make(
  <path d="M2.5 8c1.6 0 1.6 1.2 3.2 1.2S7.3 8 8.9 8s1.6 1.2 3.1 1.2S13.6 8 15.2 8s1.6 1.2 3.2 1.2S20 8 21.5 8M2.5 13c1.6 0 1.6 1.2 3.2 1.2S7.3 13 8.9 13s1.6 1.2 3.1 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.1-1.2M2.5 18c1.6 0 1.6 1.2 3.2 1.2S7.3 18 8.9 18s1.6 1.2 3.1 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.1-1.2" />,
  "IconWaves",
);
const IconTelescope = make(
  <>
    <circle cx="12" cy="12" r="1" />
    <path d="M3.5 3.5l1.5 1.5M19 5l1.5-1.5M12 2.5V4M7 18l3.5-5M17 18l-3.5-5M4.5 13l12-6.5 2 3.5-12 6.5-2-3.5z" />
  </>,
  "IconTelescope",
);
const IconSpa = make(
  <path d="M12 20c-4.5 0-8-2.5-8.5-7 2.5 0 5.5 1 8.5 4 3-3 6-4 8.5-4-.5 4.5-4 7-8.5 7zM12 17c-1.8-2-2.5-4.5-2.5-6.5S10.5 6 12 4c1.5 2 2.5 4.5 2.5 6.5S13.8 15 12 17z" />,
  "IconSpa",
);
const IconBoat = make(
  <path d="M3 15.5l1.6 4.5h14.8l1.6-4.5H3zM6 15.5V9h12v6.5M9 9V5.5h6V9M12 5.5V3" />,
  "IconBoat",
);
const IconDesk = make(
  <>
    <rect x="3.5" y="5" width="17" height="11" rx="1.5" />
    <path d="M8.5 20h7M12 16v4" />
  </>,
  "IconDesk",
);
const IconPaw = make(
  <>
    <circle cx="6" cy="10.5" r="1.8" />
    <circle cx="9.5" cy="6" r="1.8" />
    <circle cx="14.5" cy="6" r="1.8" />
    <circle cx="18" cy="10.5" r="1.8" />
    <path d="M12 12c-2.8 0-5 3.3-5 5.4 0 1.4 1 2.1 2.3 2.1 1.1 0 1.7-.6 2.7-.6s1.6.6 2.7.6c1.3 0 2.3-.7 2.3-2.1C17 15.3 14.8 12 12 12z" />
  </>,
  "IconPaw",
);
const IconBoot = make(<path d="M7 3h6v8l6 3.5c1 .6 1.5 1.5 1.5 2.5v2H4V3h3zM4 15.5h16.5M9 7h4M9 10h4" />, "IconBoot");
const IconYoga = make(
  <>
    <circle cx="12" cy="4.5" r="1.8" />
    <path d="M12 7.5v6M5 10.5l7 2 7-2M8 20l4-6.5 4 6.5M5.5 20h13" />
  </>,
  "IconYoga",
);
const IconBath = make(
  <path d="M3 12h18v2.5A5.5 5.5 0 0 1 15.5 20h-7A5.5 5.5 0 0 1 3 14.5V12zM6 12V5.5A2.5 2.5 0 0 1 10.5 4M6.5 20l-1 1.5M17.5 20l1 1.5" />,
  "IconBath",
);

const amenityRules: [RegExp, (p: IconProps) => React.ReactElement][] = [
  [/wi-?fi|internet/i, IconWifi],
  [/pool|swim/i, IconPool],
  [/hot tub|jacuzzi|bath|tub/i, IconBath],
  [/coffee|tea|plantation|estate/i, IconCoffee],
  [/fire|bonfire|hearth|campfire/i, IconFlame],
  [/breakfast|meal|chef|kitchen|dining|cuisine|food|organic/i, IconUtensils],
  [/heat|snow|cold|warm/i, IconSnow],
  [/spa|massage|ayurved|wellness/i, IconSpa],
  [/yoga|meditat/i, IconYoga],
  [/star|telescope|sky|astro/i, IconTelescope],
  [/boat|kayak|canoe|cruise|shikara/i, IconBoat],
  [/lake|river|backwater|sea|beach|ocean/i, IconWaves],
  [/park|car|transfer|pickup|airport|jeep|drive/i, IconCar],
  [/work|desk|laptop/i, IconDesk],
  [/pet|dog/i, IconPaw],
  [/trek|hike|walk|trail|guide/i, IconBoot],
  [/view|mountain|valley|himalay|peak|deck|balcony/i, IconMountain],
  [/garden|forest|nature|eco|farm|leaf/i, IconLeaf],
];

export function AmenityIcon({ name, ...rest }: IconProps & { name: string }) {
  const hit = amenityRules.find(([re]) => re.test(name));
  const Cmp = hit ? hit[1] : IconSparkle;
  return <Cmp {...rest} />;
}
