"use client";

import { useEffect, useMemo, useState } from "react";
import { fallbackDigest, fallbackResearch, type AlertItem, type NetworkMatch } from "../lib/demo";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ResearchMetric = {
  label: string;
  value: string;
  trend?: string;
};

type ResearchSource = {
  label: string;
  type: string;
  page?: string | null;
  url?: string | null;
  provenance: string;
};

type ResearchSection = {
  label: string;
  text: string;
  status: string;
  variant?: "summary" | "insight" | "evidence" | "case" | "missing";
  tone?: "bull" | "bear";
  metrics?: ResearchMetric[];
  source: ResearchSource | null;
  sources?: ResearchSource[];
};

type Research = {
  ticker: string;
  company: string | null;
  available: boolean;
  disclosure: string;
  headline: string;
  sections: ResearchSection[];
  network: NetworkMatch[];
  provenance?: string;
  model?: string;
};

type NewsArticle = {
  id?: string | null;
  title: string;
  description?: string | null;
  url?: string | null;
  publishedAt?: string | null;
  source?: { name?: string | null; url?: string | null; country?: string | null };
  provenance: string;
  useInPull: boolean;
};

const navItems = [
  { id: "today", label: "Today", icon: "◒" },
  { id: "research", label: "Research", icon: "⌕" },
  { id: "network", label: "Network", icon: "⌁" },
  { id: "news", label: "News", icon: "✦" },
];

export default function Home() {
  const [active, setActive] = useState("today");
  const [alerts, setAlerts] = useState<AlertItem[]>(fallbackDigest.items);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem>(fallbackDigest.items[0]);
  const [ticker, setTicker] = useState("TCS");
  const [research, setResearch] = useState<Research>(fallbackResearch.TCS);
  const [networkQuery, setNetworkQuery] = useState("");
  const [searchedNetwork, setSearchedNetwork] = useState<NetworkMatch[]>(fallbackResearch.TCS.network);
  const [newsArticles, setNewsArticles] = useState<NewsArticle[]>([]);
  const [newsQuery, setNewsQuery] = useState("Tata Consultancy Services");
  const [notice, setNotice] = useState("Demo data loaded — provenance is shown on every card.");

  const highPriorityCount = useMemo(() => alerts.filter((item) => item.priority === "High").length, [alerts]);

  async function loadResearch() {
    const normalized = ticker.trim().toUpperCase().replace(".NS", "").replace(".BO", "");
    if (!normalized) return;
    try {
      const response = await fetch(`${API_BASE}/research/${normalized}`);
      if (!response.ok) throw new Error("Research unavailable");
      const result = await response.json();
      setResearch(result);
      setActive("research");
      setNotice(result.available ? "Research loaded from Supabase and Gemini." : "No primary-source documents are available for this ticker.");
    } catch {
      const result = fallbackResearch[normalized as keyof typeof fallbackResearch];
      if (result) {
        setResearch(result);
      setNotice("API unavailable — showing a local cached fixture. Start the backend and press Research again.");
      } else {
        setResearch({ ticker: normalized, company: null, available: false, disclosure: "No annual-report or earnings-call transcript fixture is available for this ticker.", headline: "Evidence unavailable", sections: [], network: [] });
        setNotice("No source fixture is available for this ticker.");
      }
      setActive("research");
    }
  }

  useEffect(() => {
    void loadResearch();
  }, []);

  async function searchNetwork() {
    const normalized = ticker.trim().toUpperCase().replace(".NS", "").replace(".BO", "") || "TCS";
    try {
      const query = networkQuery ? `&query=${encodeURIComponent(networkQuery)}` : "";
      const response = await fetch(`${API_BASE}/network/matches?ticker=${normalized}${query}`);
      if (!response.ok) throw new Error("Network unavailable");
      const result = await response.json();
      setSearchedNetwork(result.matches);
    } catch {
      const fallback = fallbackResearch[normalized as keyof typeof fallbackResearch];
      setSearchedNetwork(fallback?.network ?? []);
    }
  }

  async function loadNews() {
    const params = new URLSearchParams({ query: newsQuery.trim() || "Tata Consultancy Services", max_results: "10" });
    try {
      const response = await fetch(`${API_BASE}/news?${params.toString()}`);
      if (!response.ok) throw new Error("News unavailable");
      const result = await response.json();
      setNewsArticles(result.articles ?? []);
      setNotice(result.notice ?? "News loaded from GNews.");
    } catch {
      setNewsArticles([]);
      setNotice("News is unavailable. Check the backend and GNEWS_API_KEY.");
    }
  }

  function adjustThreshold() {
    setAlerts((current) => current.map((item) => item.id === "ann-002" ? { ...item, metric: { ...item.metric, value: item.metric.value === "2.4×" ? "3.0×" : "2.4×" } } : item));
    setNotice("Unusual-volume threshold updated for this demo session.");
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">F</span><span>FINN</span></div>
        <div className="sidebar-label">INVESTOR DESK</div>
        <nav className="desktop-nav">
          {navItems.map((item) => <button key={item.id} className={`nav-item ${active === item.id ? "active" : ""}`} onClick={() => setActive(item.id)}><span>{item.icon}</span>{item.label}</button>)}
        </nav>
        <div className="sidebar-bottom"><div className="mini-status"><span className="status-dot" /> Demo environment</div><div className="user-chip"><span className="avatar">AK</span><span><strong>Analyst</strong><small>Personal workspace</small></span></div></div>
      </aside>

      <section className="content">
        <header className="topbar"><div><div className="eyebrow">SATURDAY, 14 NOVEMBER 2026</div><h1>{active === "today" ? "Good morning, Analyst" : active === "research" ? "Research desk" : active === "network" ? "Your network" : "News context"}</h1></div><button className="icon-button" aria-label="Notifications">♧<span className="notification-dot" /></button></header>
        <div className="mobile-nav">{navItems.map((item) => <button key={item.id} className={active === item.id ? "active" : ""} onClick={() => setActive(item.id)}><span>{item.icon}</span>{item.label}</button>)}</div>
        <div className="notice"><span>✦</span>{notice}</div>

        {active === "today" && <Today alerts={alerts} highPriorityCount={highPriorityCount} selectedAlert={selectedAlert} setSelectedAlert={setSelectedAlert} adjustThreshold={adjustThreshold} onResearch={(value) => { setTicker(value); loadResearch(); }} />}
        {active === "research" && <ResearchView ticker={ticker} setTicker={setTicker} research={research} loadResearch={loadResearch} onNetwork={(matches) => { setSearchedNetwork(matches); setActive("network"); }} />}
        {active === "network" && <NetworkView ticker={ticker} setTicker={setTicker} query={networkQuery} setQuery={setNetworkQuery} matches={searchedNetwork} search={searchNetwork} />}
        {active === "news" && <NewsView query={newsQuery} setQuery={setNewsQuery} articles={newsArticles} search={loadNews} />}
      </section>
    </main>
  );
}

function Today({ alerts, highPriorityCount, selectedAlert, setSelectedAlert, adjustThreshold, onResearch }: { alerts: AlertItem[]; highPriorityCount: number; selectedAlert: AlertItem; setSelectedAlert: (item: AlertItem) => void; adjustThreshold: () => void; onResearch: (ticker: string) => void }) {
  return <>
    <section className="hero-row"><div><p className="section-kicker">YOUR PORTFOLIO · LAST 24 HOURS</p><div className="hero-metric">{highPriorityCount}<span>high-priority signals</span></div><p className="muted">Across 15 tracked companies <span className="live-pill"><i /> End-of-day data</span></p></div><button className="outline-button" onClick={adjustThreshold}>⚙ Tune alerts</button></section>
    <section className="stats-grid"><div className="stat-card accent"><span>Signal quality</span><strong>Focused</strong><small>3 items surfaced</small></div><div className="stat-card"><span>Portfolio</span><strong>15</strong><small>NSE / BSE names</small></div><div className="stat-card"><span>Research ready</span><strong>3</strong><small>Primary-source sets</small></div></section>
    <section className="workspace-grid"><div className="feed-panel"><div className="panel-heading"><div><p className="section-kicker">THE SIGNAL FEED</p><h2>What changed</h2></div><button className="filter-button">24h⌄</button></div><div className="alert-list">{alerts.map((item) => <button key={item.id} className={`alert-card ${selectedAlert.id === item.id ? "selected" : ""}`} onClick={() => setSelectedAlert(item)}><div className={`priority-bar ${item.priority.toLowerCase()}`} /><div className="alert-main"><div className="alert-topline"><span className="tag">{item.kind}</span><span className="priority-text">{item.priority} priority</span></div><h3>{item.title}</h3><p>{item.summary}</p><div className="card-foot"><span>{item.ticker} · {item.company}</span><span className={`metric ${item.metric.tone}`}>{item.metric.label} <strong>{item.metric.value}</strong></span></div></div><span className="chevron">›</span></button>)}</div></div><DetailPanel alert={selectedAlert} onResearch={onResearch} /></section>
  </>;
}

function DetailPanel({ alert, onResearch }: { alert: AlertItem; onResearch: (ticker: string) => void }) {
  return <aside className="detail-panel"><div className="panel-heading"><div><p className="section-kicker">WHY IT MATTERS</p><h2>{alert.ticker}</h2></div><span className="detail-kind">{alert.kind}</span></div><p className="detail-summary">{alert.impact}</p><div className="detail-metric"><span>{alert.metric.label}</span><strong>{alert.metric.value}</strong></div><div className="evidence-box"><div className="evidence-title"><span className="verified-icon">✓</span><strong>Evidence trail</strong></div><p>{alert.source.label} · {alert.source.page ?? "end-of-day"}</p><span className="provenance">{alert.source.provenance}</span></div><div className="network-block"><div className="block-heading"><div><p className="section-kicker">NETWORK SIGNAL</p><h3>Who can help?</h3></div><span className="network-icon">⌁</span></div>{alert.network.slice(0, 2).map((person) => <NetworkRow key={person.name} person={person} />)}</div><button className="primary-button" onClick={() => onResearch(alert.ticker)}>Research {alert.ticker} <span>→</span></button></aside>;
}

function NetworkRow({ person }: { person: NetworkMatch }) {
  return <div className="network-row"><span className="avatar person-avatar">{person.name.split(" ").map((part) => part[0]).join("")}</span><span className="network-copy"><strong>{person.name}</strong><small>{person.role}</small><em>{person.evidence} · {person.score}% relevance</em></span><span className="row-arrow">›</span></div>;
}

const REQUIRED_INSIGHTS = [
  { label: "Business snapshot", aliases: ["business snapshot"] },
  { label: "Financial snapshot", aliases: ["financial snapshot", "financial trajectory"] },
  { label: "Trajectory", aliases: ["trajectory"] },
  { label: "Balance sheet", aliases: ["balance sheet"] },
  { label: "Cash quality", aliases: ["cash quality"] },
  { label: "Narrative vs. numbers", aliases: ["narrative vs. numbers", "narrative vs numbers"] },
  { label: "Guidance", aliases: ["guidance"] },
];

function ResearchCitations({ section }: { section: ResearchSection }) {
  const sources = section.sources?.length ? section.sources : section.source ? [section.source] : [];
  if (sources.length) {
    return <div className="citation-list">{sources.slice(0, 3).map((source, index) => source.url ? <a className="citation" href={source.url} target="_blank" rel="noreferrer" key={`${source.label}-${index}`}>↗ {source.label} · {source.page ?? "source"}</a> : <div className="citation" key={`${source.label}-${index}`}>↗ {source.label} · {source.page ?? "source"}</div>)}</div>;
  }
  if (section.status === "Interpreted") return <div className="citation derived">✦ Derived from the cited primary-source evidence</div>;
  return <div className="citation missing">No supporting evidence loaded</div>;
}

function ResearchCard({ section }: { section: ResearchSection }) {
  return <article className={`research-card ${section.variant ?? "insight"}`}><div className="card-topline"><span className="section-kicker">{section.label}</span><span className={`status-label ${section.status.toLowerCase().replace(" ", "-")}`}>{section.status}</span></div><p>{section.text}</p>{section.metrics?.length ? <div className="metric-strip">{section.metrics.slice(0, 4).map((metric) => <div className={`research-metric ${metric.trend ?? "neutral"}`} key={`${metric.label}-${metric.value}`}><small>{metric.label}</small><strong>{metric.value}</strong><em>{metric.trend && metric.trend !== "neutral" ? metric.trend : "reported"}</em></div>)}</div> : null}<ResearchCitations section={section} /></article>;
}

function CaseCard({ section }: { section: ResearchSection }) {
  return <article className={`case-card ${section.tone ?? "bull"}`}><div className="case-card-head"><span className="case-marker">{section.tone === "bear" ? "↓" : "↑"}</span><div><p className="section-kicker">{section.label}</p><span className="case-caption">Scenario interpretation</span></div></div><p>{section.text}</p><ResearchCitations section={section} /></article>;
}

function ResearchView({ ticker, setTicker, research, loadResearch, onNetwork }: { ticker: string; setTicker: (value: string) => void; research: Research; loadResearch: () => void; onNetwork: (matches: NetworkMatch[]) => void }) {
  const isLive = research.provenance?.startsWith("Gemini interpretation");
  const summary = research.sections.find((section) => section.variant === "summary" || section.label.toLowerCase() === "research summary") ?? { label: "Research summary", text: research.headline, status: "Interpreted", source: null, variant: "summary" as const };
  const rawInsights = research.sections.filter((section) => section.variant === "insight" || (!section.variant && !section.label.toLowerCase().includes("evidence") && !section.label.toLowerCase().includes("bull")));
  const insights = REQUIRED_INSIGHTS.map((required) => rawInsights.find((section) => required.aliases.includes(section.label.toLowerCase())) ?? { label: required.label, text: "No verified evidence is available in the supplied primary-source documents.", status: "Unavailable", source: null, sources: [], variant: "insight" as const });
  const evidence = research.sections.filter((section) => section.variant === "evidence" || (!section.variant && section.label.toLowerCase().includes("evidence")));
  let cases = research.sections.filter((section) => section.variant === "case");
  const legacyCase = research.sections.find((section) => section.label.toLowerCase().includes("bull / bear"));
  if (!cases.length && legacyCase) cases = [{ ...legacyCase, label: "Bull case", tone: "bull", variant: "case" }, { ...legacyCase, label: "Bear case", tone: "bear", variant: "case" }];
  const missing = research.sections.filter((section) => section.variant === "missing");

  return <section className="research-view"><div className="research-header"><div><p className="section-kicker">PULL · PRIMARY-SOURCE RESEARCH</p><h2>Understand a company</h2><p className="muted">Annual reports and earnings-call transcripts only. News remains contextual and is excluded from this view.</p></div><div className="ticker-search"><input value={ticker} onChange={(event) => setTicker(event.target.value)} onKeyDown={(event) => event.key === "Enter" && loadResearch()} placeholder="NSE ticker" aria-label="NSE ticker" /><button onClick={loadResearch}>Research</button></div></div>{research.available ? <><div className="research-title"><div><span className="ticker-badge">{research.ticker}</span><h2>{research.company}</h2></div><span className="provenance">{isLive ? "LIVE · SUPABASE + GEMINI" : "SYNTHETIC DEMO"}</span></div><div className="disclosure"><span>ⓘ</span>{research.disclosure}</div><div className="research-overview"><article className="summary-card"><div className="summary-card-top"><div><p className="section-kicker">RESEARCH SUMMARY</p><h3>What matters first</h3></div><span className="summary-icon">✦</span></div><p>{summary.text}</p><ResearchCitations section={summary} /></article><aside className="reading-card"><p className="section-kicker">HOW TO READ THIS VIEW</p><h3>Facts first. Interpretation second.</h3><div className="reading-row"><span className="reading-dot fact" /><span><strong>Evidence</strong><small>Directly tied to a report or transcript page.</small></span></div><div className="reading-row"><span className="reading-dot interpretation" /><span><strong>Interpreted</strong><small>Gemini synthesis of the cited primary-source excerpts.</small></span></div><div className="reading-row"><span className="reading-dot missing" /><span><strong>Unavailable</strong><small>Not supported by the documents loaded for this company.</small></span></div></aside></div><div className="research-subheading"><div><p className="section-kicker">THE RESEARCH MAP</p><h3>Eight ways to understand the company</h3></div><span className="muted">Primary-source view</span></div><div className="research-grid insight-grid">{insights.map((section) => <ResearchCard section={section} key={section.label} />)}</div>{cases.length ? <><div className="research-subheading case-heading"><div><p className="section-kicker">SCENARIO FRAME</p><h3>Bull versus bear</h3></div><span className="muted">Interpretation, not a recommendation</span></div><div className="case-grid">{cases.map((section) => <CaseCard section={section} key={`${section.label}-${section.tone}`} />)}</div></> : null}{evidence.length ? <><div className="research-subheading evidence-heading"><div><p className="section-kicker">SOURCE TRAIL</p><h3>Evidence cards</h3></div><span className="muted">Claims tied to retrieved pages</span></div><div className="evidence-grid">{evidence.map((section) => <ResearchCard section={section} key={section.label} />)}</div></> : null}{missing.length ? <div className="missing-evidence"><div><p className="section-kicker">OPEN QUESTIONS</p><h3>What the documents do not establish</h3></div>{missing.map((section) => <div className="missing-item" key={section.label}><strong>{section.label}</strong><span>{section.text}</span></div>)}</div> : null}<div className="research-network"><div><p className="section-kicker">NETWORK CONTEXT</p><h3>Who can help me understand {research.ticker}?</h3><p className="muted">Matches are ranked from explicit synthetic profile evidence.</p></div><div className="research-network-list">{research.network.map((person) => <NetworkRow key={person.name} person={person} />)}</div><button className="outline-button" onClick={() => onNetwork(research.network)}>Open network view →</button></div></> : <div className="empty-state"><span className="empty-icon">⌕</span><h3>Evidence unavailable</h3><p>{research.disclosure}</p><p>Try another tracked company with an ingested annual report.</p></div>}</section>;
}

function NetworkView({ ticker, setTicker, query, setQuery, matches, search }: { ticker: string; setTicker: (value: string) => void; query: string; setQuery: (value: string) => void; matches: NetworkMatch[]; search: () => void }) {
  return <section className="network-view"><div className="research-header"><div><p className="section-kicker">NETWORK · CONTEXTUAL ADVANTAGE</p><h2>Who should I call?</h2><p className="muted">Relevant context, with the evidence shown alongside the suggestion.</p></div></div><div className="network-search"><div><label>Company or ticker</label><input value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="TCS" /></div><div><label>What do you need to understand?</label><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. delivery economics" /></div><button className="primary-button" onClick={search}>Find context <span>→</span></button></div><div className="network-result-heading"><div><p className="section-kicker">MATCHES FOR {ticker.toUpperCase()}</p><h3>People who may help</h3></div><span className="provenance">Synthetic profiles</span></div><div className="network-results">{matches.length ? matches.map((person) => <article className="large-network-card" key={person.name}><span className="avatar person-avatar large">{person.name.split(" ").map((part) => part[0]).join("")}</span><div className="large-network-copy"><div className="card-topline"><span className="tag">{person.evidence}</span><strong>{person.score}% relevance</strong></div><h3>{person.name}</h3><p>{person.role}</p><div className="reason-box"><strong>Why this match</strong><span>{person.reason}</span></div><small>{person.caveat}</small></div></article>) : <div className="empty-state small"><h3>No relevant match found</h3><p>Try a seeded company such as TCS, RELIANCE, or INFY.</p></div>}</div></section>;
}

function NewsView({ query, setQuery, articles, search }: { query: string; setQuery: (value: string) => void; articles: NewsArticle[]; search: () => void }) {
  return <section className="news-view"><div className="research-header"><div><p className="section-kicker">NEWS · CONTEXT ONLY</p><h2>What is being said?</h2><p className="muted">GNews articles help you monitor context. They are never used as evidence for Pull analysis.</p></div></div><div className="news-search"><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && search()} placeholder="Company, sector, or theme" aria-label="News search" /><button className="primary-button" onClick={search}>Search news <span>→</span></button></div>{articles.length ? <div className="news-list">{articles.map((article) => <article className="news-card" key={article.id ?? article.url ?? article.title}><div className="card-topline"><span className="tag">{article.source?.name ?? "News source"}</span><span className="provenance">{article.provenance}</span></div><h3>{article.title}</h3>{article.description && <p>{article.description}</p>}<div className="news-foot"><span>{article.publishedAt ? new Date(article.publishedAt).toLocaleString() : "Publication time unavailable"}</span>{article.url && <a href={article.url} target="_blank" rel="noreferrer">Open source ↗</a>}</div></article>)}</div> : <div className="empty-state"><span className="empty-icon">✦</span><h3>Search for context</h3><p>Enter a company or theme, then search GNews through the backend.</p><p className="muted">The API key stays server-side; news is excluded from Pull.</p></div>}</section>;
}
