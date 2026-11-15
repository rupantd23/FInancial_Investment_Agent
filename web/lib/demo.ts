export type Source = {
  label: string;
  type: string;
  page?: string | null;
  url?: string | null;
  provenance: string;
};

export type NetworkMatch = {
  personId?: string;
  name: string;
  role: string;
  score: number;
  reason: string;
  evidence: string;
  source?: string;
  caveat: string;
};

export type AlertItem = {
  id: string;
  ticker: string;
  company: string;
  kind: string;
  priority: string;
  title: string;
  summary: string;
  impact: string;
  metric: { label: string; value: string; tone: string };
  source: Source;
  network: NetworkMatch[];
};

export const fallbackDigest = {
  window: "24h",
  generatedAt: new Date().toISOString(),
  provenance: "Synthetic demo fixture",
  portfolioCount: 15,
  items: [
    {
      id: "ann-001",
      ticker: "TCS",
      company: "Tata Consultancy Services",
      kind: "Quarterly results",
      priority: "High",
      title: "Results filing: headline metrics need a closer look",
      summary: "A results filing was added to the digest. FINN extracted the four headline metrics for comparison.",
      impact: "Compare delivery against management commentary before changing the investment view.",
      metric: { label: "PAT YoY", value: "+8.4%", tone: "positive" },
      source: { label: "Synthetic results filing", type: "annual_report", page: "p. 3", url: null, provenance: "Synthetic demo fixture" },
      network: [{ name: "Neha Rao", role: "Former enterprise software executive", score: 88, reason: "Worked at a synthetic TCS fixture and later at a large enterprise buyer.", evidence: "Employer and customer overlap", caveat: "This is a relevance signal, not a claim of personal contact." }],
    },
    {
      id: "ann-002",
      ticker: "RELIANCE",
      company: "Reliance Industries",
      kind: "Unusual volume",
      priority: "High",
      title: "Volume crossed your unusual-move threshold",
      summary: "End-of-day volume is 2.4× its 20-day average in this synthetic fixture.",
      impact: "Check the latest company filing and avoid treating volume alone as an explanation.",
      metric: { label: "Volume vs avg", value: "2.4×", tone: "warning" },
      source: { label: "Synthetic market data", type: "market_data", page: null, url: null, provenance: "Synthetic demo fixture" },
      network: [{ name: "Asha Mehta", role: "Former digital infrastructure operator", score: 92, reason: "Worked at a synthetic Reliance Digital Infrastructure fixture from 2021–2023.", evidence: "Employer overlap", caveat: "Employer overlap indicates relevance, not proof of a personal relationship." }],
    },
    {
      id: "ann-003",
      ticker: "INFY",
      company: "Infosys",
      kind: "Management change",
      priority: "Medium",
      title: "Incoming finance leader added to the watchlist",
      summary: "A management-change announcement is available for review.",
      impact: "Use the background card to identify relevant operating context before a conversation.",
      metric: { label: "Network relevance", value: "1 strong match", tone: "neutral" },
      source: { label: "Synthetic exchange announcement", type: "announcement", page: "p. 1", url: null, provenance: "Synthetic demo fixture" },
      network: [{ name: "Vikram Singh", role: "Technology services operator", score: 84, reason: "Former employer and sector overlap with IT services delivery.", evidence: "Employer overlap", caveat: "Employer overlap indicates relevance, not proof of a personal relationship." }],
    },
  ] as AlertItem[],
};

export const fallbackResearch = {
  TCS: {
    ticker: "TCS", company: "Tata Consultancy Services", available: true,
    disclosure: "Synthetic demo analysis. Replace with extracted annual-report and transcript evidence before submission.",
    headline: "A resilient services profile with a question around delivery against guidance.",
    sections: [
      { label: "Business snapshot", text: "Synthetic evidence describes a diversified enterprise technology-services business across multiple client sectors.", status: "Interpreted", source: { label: "Synthetic annual report excerpt", type: "annual_report", page: "p. 12", provenance: "Synthetic demo fixture" } },
      { label: "Financial trajectory", text: "Revenue and PAT are shown as stable-to-growing in the demo fixture; replace these values with extracted company figures.", status: "Synthetic demo", source: { label: "Synthetic results excerpt", type: "annual_report", page: "p. 34", provenance: "Synthetic demo fixture" } },
      { label: "Narrative vs numbers", text: "Management commentary emphasizes resilience. The next implementation step is to compare the last four quarters with explicit guidance from transcripts.", status: "Interpreted", source: { label: "Synthetic earnings-call excerpt", type: "earnings_call_transcript", page: "p. 5", provenance: "Synthetic demo fixture" } },
      { label: "Bull / bear", text: "Bull: diversified demand and execution. Bear: slower discretionary technology spending could pressure growth.", status: "Interpreted", source: { label: "Synthetic transcript excerpt", type: "earnings_call_transcript", page: "p. 8", provenance: "Synthetic demo fixture" } },
    ],
    network: [{ name: "Neha Rao", role: "Former enterprise software executive", score: 88, reason: "Worked at a synthetic TCS fixture and later at a large enterprise buyer.", evidence: "Employer and customer overlap", caveat: "This is a relevance signal, not a claim of personal contact." }],
  },
  RELIANCE: {
    ticker: "RELIANCE", company: "Reliance Industries", available: true,
    disclosure: "Synthetic demo analysis. Replace with extracted annual-report and transcript evidence before submission.",
    headline: "A diversified company where the key research task is separating segment narratives.",
    sections: [
      { label: "Business snapshot", text: "Synthetic evidence describes a diversified group with energy, consumer, and digital infrastructure activities.", status: "Interpreted", source: { label: "Synthetic annual report excerpt", type: "annual_report", page: "p. 9", provenance: "Synthetic demo fixture" } },
      { label: "Narrative vs numbers", text: "The demo flags a need to compare segment commentary with reported operating performance rather than relying on a single consolidated headline.", status: "Interpreted", source: { label: "Synthetic earnings-call excerpt", type: "earnings_call_transcript", page: "p. 4", provenance: "Synthetic demo fixture" } },
      { label: "Bull / bear", text: "Bull: multiple growth engines. Bear: complexity makes evidence quality and segment attribution more important.", status: "Interpreted", source: { label: "Synthetic transcript excerpt", type: "earnings_call_transcript", page: "p. 7", provenance: "Synthetic demo fixture" } },
    ],
    network: [{ name: "Asha Mehta", role: "Former digital infrastructure operator", score: 92, reason: "Worked at a synthetic Reliance Digital Infrastructure fixture from 2021–2023.", evidence: "Employer overlap", caveat: "Employer overlap indicates relevance, not proof of a personal relationship." }],
  },
  INFY: {
    ticker: "INFY", company: "Infosys", available: true,
    disclosure: "Synthetic demo analysis. Replace with extracted annual-report and transcript evidence before submission.",
    headline: "A technology-services research view focused on demand, margins, and delivery commentary.",
    sections: [
      { label: "Business snapshot", text: "Synthetic evidence describes an international technology-services business with enterprise clients.", status: "Interpreted", source: { label: "Synthetic annual report excerpt", type: "annual_report", page: "p. 11", provenance: "Synthetic demo fixture" } },
      { label: "Guidance", text: "No verified guidance is available in this fixture; FINN should show the missing-evidence state until a transcript is loaded.", status: "Unavailable", source: null },
      { label: "Bull / bear", text: "Bull: resilient client relationships. Bear: discretionary-spend weakness may delay large programs.", status: "Interpreted", source: { label: "Synthetic transcript excerpt", type: "earnings_call_transcript", page: "p. 6", provenance: "Synthetic demo fixture" } },
    ],
    network: [{ name: "Vikram Singh", role: "Technology services operator", score: 84, reason: "Former employer and sector overlap with IT services delivery.", evidence: "Employer overlap", caveat: "Employer overlap indicates relevance, not proof of a personal relationship." }],
  },
};
