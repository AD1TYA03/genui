const u = (id: string, w = 1000) => `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=${w}&q=80`;

export interface Destination {
  title: string;
  region: string;
  blurb: string;
  prompt: string;
  image: string;
}

/** Empty-state tiles. Image URLs verified to return HTTP 200. */
export const DESTINATIONS: Destination[] = [
  {
    title: "Himalayan treehouses",
    region: "Himachal Pradesh",
    blurb: "Cedar, woodsmoke, snowlines",
    prompt: "Find me a cosy treehouse in the Himalayas with a fireplace",
    image: u("1510798831971-661eb04b3739", 1200),
  },
  {
    title: "Kerala houseboats",
    region: "Alleppey backwaters",
    blurb: "Slow days on palm-fringed water",
    prompt: "I want a private houseboat on the Kerala backwaters",
    image: u("1602216056096-3b40cc0c9944"),
  },
  {
    title: "Desert domes",
    region: "Rann of Kutch",
    blurb: "Salt flats & a sky full of stars",
    prompt: "Show me desert domes for stargazing in Kutch or Jaisalmer",
    image: u("1473580044384-7ba9967e16a0"),
  },
  {
    title: "Ladakh glamping",
    region: "Pangong · Nubra",
    blurb: "Canvas suites at 4,000 m",
    prompt: "Luxury glamping in Ladakh near Pangong lake",
    image: u("1504280390367-361c6d9f38f4"),
  },
  {
    title: "Coffee-estate cottages",
    region: "Coorg, Karnataka",
    blurb: "Mist, monsoon & estate brews",
    prompt: "A quiet cottage on a coffee estate in Coorg",
    image: u("1596394516093-501ba68a0ba6"),
  },
  {
    title: "Spiti mud homes",
    region: "Spiti Valley",
    blurb: "Monasteries & moonscapes",
    prompt: "Traditional mud homes in Spiti valley for a slow week",
    image: u("1544735716-392fe2489ffa"),
  },
];

export const STARTER_CHIPS = [
  "Weekend escape under ₹15k a night",
  "Somewhere romantic for an anniversary",
  "Family trip with two kids in December",
  "Surprise me",
];
