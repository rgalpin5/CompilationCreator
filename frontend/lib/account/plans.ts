/** What the pricing section offers. Edit prices and copy here. */
export type Plan = {
  id: string;
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  features: string[];
  available: boolean;
};

export const LIFETIME_PLAN: Plan = {
  id: "lifetime",
  name: "Lifetime",
  price: "$29",
  cadence: "one-time",
  blurb: "Everything in the studio, yours to keep.",
  features: [
    "Unlimited compilations",
    "Up to 100 clips and 4 hours per export",
    "Frame-accurate intro and outro trimming",
    "1080p and 4K output",
    "Export history and per-video usage log",
    "Every update to the current studio",
  ],
  available: true,
};

export const PRO_PLAN: Plan = {
  id: "pro",
  name: "Pro",
  price: "TBA",
  cadence: "monthly",
  blurb: "Extra features on top of Lifetime, as a subscription.",
  features: ["Everything in Lifetime", "Cloud delivery of finished videos", "Scheduled compilations"],
  available: false,
};
