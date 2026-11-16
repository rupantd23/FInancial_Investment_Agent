"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { fallbackResearch, portfolioCompanies, type AlertItem, type NetworkMatch, type PortfolioCompany } from "../lib/demo";
import { getSupabaseClient } from "../lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const supabase = getSupabaseClient();
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;
  const headers = new Headers(init.headers);
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

async function apiError(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: string | { message?: string } } | null;
  const detail = typeof payload?.detail === "string" ? payload.detail : payload?.detail?.message;
  return detail || `${fallback} (${response.status})`;
}

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

type NetworkContact = {
  id: string;
  display_name: string;
  email?: string | null;
  role_title?: string | null;
  company_name?: string | null;
  sector?: string | null;
  skills?: string[];
  linkedin_url?: string | null;
  relationship?: string | null;
  notes?: string | null;
  provenance: string;
  source_label?: string | null;
};

type CsvPreview = {
  filename: string | null;
  row_count: number;
  valid_rows: Array<Record<string, unknown>>;
  errors: string[];
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

type MarketCompany = {
  ticker: string;
  name: string;
  sector?: string | null;
  price: number;
  change_percent: number;
  trading_date: string;
  series: number[];
  source: string;
  provenance: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  sources?: Array<{ label: string; page?: string | null; url?: string | null }>;
};

type ThemePreference = "light" | "dark" | "system";

const navItems = [
  { id: "today", label: "Today", icon: "◒" },
  { id: "market", label: "Market", icon: "⌁" },
  { id: "research", label: "Research", icon: "⌕" },
  { id: "network", label: "Network", icon: "⌁" },
  { id: "news", label: "News", icon: "◇" },
  { id: "ask", label: "Ask FINN", icon: "✦" },
];

export default function Home() {
  const [authReady, setAuthReady] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [active, setActive] = useState("today");
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [opportunities, setOpportunities] = useState<AlertItem[]>([]);
  const [marketCompanies, setMarketCompanies] = useState<MarketCompany[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [trackedCompanies, setTrackedCompanies] = useState<PortfolioCompany[]>(portfolioCompanies);
  const [ticker, setTicker] = useState("TCS");
  const [research, setResearch] = useState<Research>(fallbackResearch.TCS);
  const [networkQuery, setNetworkQuery] = useState("");
  const [searchedNetwork, setSearchedNetwork] = useState<NetworkMatch[]>(fallbackResearch.TCS.network);
  const [networkPeople, setNetworkPeople] = useState<NetworkContact[]>([]);
  const [newsArticles, setNewsArticles] = useState<NewsArticle[]>([]);
  const [newsQuery, setNewsQuery] = useState("Tata Consultancy Services");
  const [notice, setNotice] = useState("Loading live primary-source signals…");
  const [theme, setTheme] = useState<ThemePreference>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatBusy, setChatBusy] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const highPriorityCount = useMemo(() => alerts.filter((item) => item.priority === "High").length, [alerts]);

  useEffect(() => {
    const saved = window.localStorage.getItem("finn-theme") as ThemePreference | null;
    if (saved === "light" || saved === "dark" || saved === "system") setTheme(saved);
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const applyTheme = () => {
      const resolved = theme === "system" ? (media.matches ? "dark" : "light") : theme;
      setResolvedTheme(resolved);
      document.documentElement.dataset.theme = resolved;
      document.documentElement.style.colorScheme = resolved;
    };
    applyTheme();
    if (theme !== "system") return;
    media.addEventListener("change", applyTheme);
    return () => media.removeEventListener("change", applyTheme);
  }, [theme]);

  function changeTheme(value: ThemePreference) {
    setTheme(value);
    window.localStorage.setItem("finn-theme", value);
  }

  function toggleTheme() {
    changeTheme(resolvedTheme === "dark" ? "light" : "dark");
  }

  function navigateTo(section: string) {
    setActive(section);
    setMobileMenuOpen(false);
  }

  useEffect(() => {
    const supabase = getSupabaseClient();
    if (!supabase) {
      setAuthReady(true);
      return;
    }
    let mounted = true;
    void supabase.auth.getSession().then(({ data: { session } }) => {
      if (!mounted) return;
      if (!session) {
        window.location.replace("/login");
        return;
      }
      setUserEmail(session.user.email ?? "Analyst");
      setActive("today");
      setAuthReady(true);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        window.location.replace("/login");
      } else {
        setUserEmail(session.user.email ?? "Analyst");
        setActive("today");
        setAuthReady(true);
      }
    });
    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  async function loadResearch(requestedTicker = ticker) {
    const normalized = requestedTicker.trim().toUpperCase().replace(".NS", "").replace(".BO", "");
    if (!normalized) return;
    try {
      const response = await apiFetch(`/research/${normalized}`);
      if (!response.ok) {
        const message = await apiError(response, "Research API request failed");
        setResearch({ ticker: normalized, company: null, available: false, disclosure: message, headline: "Research unavailable", sections: [], network: [] });
        setNotice(message);
        setActive("research");
        return;
      }
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
    if (authReady) void loadResearch();
  }, [authReady]);

  async function loadDigest() {
    try {
      const response = await apiFetch("/digest?window=24h");
      if (!response.ok) throw new Error(await apiError(response, "Primary-source feed request failed"));
      const result = await response.json();
      const items = Array.isArray(result.items) ? result.items as AlertItem[] : [];
      setAlerts(items);
      setSelectedAlert(items[0] ?? null);
      setNotice(result.notice ?? "Live primary-source signals loaded from Supabase.");
    } catch (caught) {
      setAlerts([]);
      setSelectedAlert(null);
      setNotice(caught instanceof Error ? caught.message : "Primary-source feed is unavailable. No synthetic fallback was loaded.");
    }
  }

  useEffect(() => {
    if (authReady) void loadDigest();
  }, [authReady]);

  async function loadOpportunities() {
    try {
      const response = await apiFetch("/opportunities?limit=8");
      if (!response.ok) throw new Error(await apiError(response, "Opportunity feed request failed"));
      const result = await response.json();
      setOpportunities(Array.isArray(result.items) ? result.items as AlertItem[] : []);
    } catch {
      setOpportunities([]);
    }
  }

  useEffect(() => {
    if (authReady) void loadOpportunities();
  }, [authReady]);

  async function loadMarket() {
    try {
      const response = await apiFetch("/market?limit=20");
      if (!response.ok) throw new Error(await apiError(response, "Market dashboard request failed"));
      const result = await response.json();
      setMarketCompanies(Array.isArray(result.companies) ? result.companies as MarketCompany[] : []);
    } catch {
      setMarketCompanies([]);
    }
  }

  async function refreshMarket() {
    const response = await apiFetch("/market/refresh", { method: "POST" });
    if (!response.ok) throw new Error(await apiError(response, "Market refresh failed"));
    await loadMarket();
    await loadOpportunities();
    setNotice("Latest EOD market prices loaded.");
  }

  useEffect(() => {
    if (authReady) void loadMarket();
  }, [authReady]);

  async function askFinn(question: string, ticker?: string) {
    const trimmed = question.trim();
    if (!trimmed || chatBusy) return;
    setChatMessages((current) => [...current, { role: "user", text: trimmed }]);
    setChatBusy(true);
    try {
      const response = await apiFetch("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: trimmed, ticker: ticker || undefined }) });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : result.detail?.message ?? "Ask FINN is unavailable");
      setChatMessages((current) => [...current, { role: "assistant", text: result.answer, sources: result.sources ?? [] }]);
    } catch (caught) {
      setChatMessages((current) => [...current, { role: "assistant", text: caught instanceof Error ? caught.message : "Ask FINN is unavailable. Please try again." }]);
    } finally {
      setChatBusy(false);
    }
  }

  function openResearch(value: string) {
    const normalized = value.trim().toUpperCase().replace(".NS", "").replace(".BO", "");
    setTicker(normalized);
    const matchingAlert = alerts.find((item) => item.ticker === normalized);
    if (matchingAlert) setSelectedAlert(matchingAlert);
    setActive("research");
    void loadResearch(normalized);
  }

  async function loadNetworkPeople() {
    try {
      const response = await apiFetch("/network/people");
      if (!response.ok) throw new Error("Network unavailable");
      const result = await response.json();
      setNetworkPeople(result.contacts ?? []);
    } catch {
      setNetworkPeople([]);
    }
  }

  useEffect(() => {
    if (authReady) void loadNetworkPeople();
  }, [authReady]);

  async function loadPortfolio() {
    try {
      const response = await apiFetch("/portfolio/companies");
      if (!response.ok) return;
      const result = await response.json();
      if (Array.isArray(result.companies) && result.companies.length) setTrackedCompanies(result.companies);
    } catch {
      // The static universe remains usable when portfolio persistence is unavailable.
    }
  }

  useEffect(() => {
    if (authReady) void loadPortfolio();
  }, [authReady]);

  useEffect(() => {
    if (!authReady) return;
    const params = new URLSearchParams(window.location.search);
    const status = params.get("linkedin");
    const message = params.get("message");
    if (status === "connected" || status === "error") {
      setNotice(message || (status === "connected" ? "LinkedIn import completed." : "LinkedIn import failed."));
      window.history.replaceState({}, "", window.location.pathname);
      if (status === "connected") void loadNetworkPeople();
    }
  }, [authReady]);

  async function searchNetwork() {
    const normalized = ticker.trim().toUpperCase().replace(".NS", "").replace(".BO", "") || "TCS";
    try {
      const query = networkQuery ? `&query=${encodeURIComponent(networkQuery)}` : "";
      const response = await apiFetch(`/network/matches?ticker=${normalized}${query}`);
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
      const response = await apiFetch(`/news?${params.toString()}`);
      if (!response.ok) {
        setNewsArticles([]);
        setNotice(await apiError(response, "News API request failed"));
        return;
      }
      const result = await response.json();
      setNewsArticles(result.articles ?? []);
      setNotice(result.notice ?? "News loaded from GNews.");
    } catch {
      setNewsArticles([]);
      setNotice("News is unavailable. Check the backend and GNEWS_API_KEY.");
    }
  }

  useEffect(() => {
    if (authReady && active === "news" && !newsArticles.length) void loadNews();
  }, [active, authReady]);

  async function connectLinkedIn() {
    try {
      const response = await apiFetch("/auth/linkedin/start");
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "LinkedIn is not available yet.");
      window.location.assign(result.authorization_url);
    } catch (caught) {
      setNotice(caught instanceof Error ? caught.message : "LinkedIn connection could not start.");
    }
  }

  async function addCompany(query: string): Promise<{ company: PortfolioCompany; research_ready: boolean; message: string }> {
    const response = await apiFetch("/portfolio/companies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail ?? "Could not add company");
    setTrackedCompanies((current) => current.some((item) => item.ticker === result.company.ticker) ? current : [...current, result.company]);
    setNotice(result.message);
    return result;
  }

  async function signOut() {
    const supabase = getSupabaseClient();
    if (supabase) await supabase.auth.signOut();
    window.location.replace("/login");
  }

  if (!authReady) return <main className="auth-shell"><section className="auth-card"><div className="brand auth-brand"><span className="brand-mark">F</span><span>FINN</span></div><p className="auth-subtitle">Loading your private workspace…</p></section></main>;
  if (!getSupabaseClient()) return <main className="auth-shell"><section className="auth-card"><div className="brand auth-brand"><span className="brand-mark">F</span><span>FINN</span></div><p className="auth-error">Supabase Auth is not configured. Add the public Supabase values to web/.env.local and restart Next.js.</p></section></main>;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">F</span><span>FINN</span></div>
        <div className="sidebar-label">INVESTOR DESK</div>
        <nav className="desktop-nav">
          {navItems.map((item) => <button key={item.id} className={`nav-item ${active === item.id ? "active" : ""}`} onClick={() => setActive(item.id)}><span>{item.icon}</span>{item.label}</button>)}
        </nav>
        <div className="sidebar-bottom"><div className="mini-status"><span className="status-dot" /> Private workspace</div><button className="user-chip user-chip-button" onClick={() => void signOut()}><span className="avatar">{(userEmail[0] ?? "A").toUpperCase()}</span><span><strong>{userEmail || "Analyst"}</strong><small>Sign out</small></span></button></div>
      </aside>

      <section className="content">
        <header className="topbar"><div><div className="eyebrow">SATURDAY, 14 NOVEMBER 2026</div><h1>{active === "today" ? "Good morning, Analyst" : active === "market" ? "Market dashboard" : active === "ask" ? "Ask FINN" : active === "research" ? "Research desk" : active === "network" ? "Your network" : "News context"}</h1></div><button className="theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`} title={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`}><span aria-hidden="true">{resolvedTheme === "dark" ? "☀" : "☾"}</span></button></header>
        <button className="mobile-menu-toggle" onClick={() => setMobileMenuOpen(true)} aria-expanded={mobileMenuOpen} aria-controls="mobile-section-menu"><span aria-hidden="true">☰</span><span>Sections</span><strong>{navItems.find((item) => item.id === active)?.label}</strong></button>
        {mobileMenuOpen && <button className="mobile-drawer-scrim" aria-label="Close section menu" onClick={() => setMobileMenuOpen(false)} />}
        <aside id="mobile-section-menu" className={`mobile-drawer ${mobileMenuOpen ? "open" : ""}`} aria-hidden={!mobileMenuOpen}><div className="mobile-drawer-head"><strong>FINN</strong><button onClick={() => setMobileMenuOpen(false)} aria-label="Close section menu">×</button></div><nav>{navItems.map((item) => <button key={item.id} className={active === item.id ? "active" : ""} onClick={() => navigateTo(item.id)}><span>{item.icon}</span>{item.label}</button>)}</nav></aside>
        <div className="notice"><span>✦</span>{notice}</div>

        {active === "today" && <Today alerts={alerts} opportunities={opportunities} highPriorityCount={highPriorityCount} selectedAlert={selectedAlert} setSelectedAlert={setSelectedAlert} trackedCompanies={trackedCompanies} onResearch={openResearch} onAddCompany={addCompany} refreshMarket={refreshMarket} />}
        {active === "market" && <MarketView companies={marketCompanies} onResearch={openResearch} refresh={refreshMarket} />}
        {active === "ask" && <AskFinn messages={chatMessages} busy={chatBusy} onAsk={askFinn} />}
        {active === "research" && <ResearchView ticker={ticker} setTicker={setTicker} research={research} loadResearch={loadResearch} marketCompany={marketCompanies.find((company) => company.ticker === research.ticker)} trackedCompanies={trackedCompanies} onBack={() => setActive("market")} onNetwork={(matches) => { setSearchedNetwork(matches); setActive("network"); }} />}
        {active === "network" && <NetworkView ticker={ticker} setTicker={setTicker} query={networkQuery} setQuery={setNetworkQuery} matches={searchedNetwork} search={searchNetwork} contacts={networkPeople} refreshContacts={loadNetworkPeople} onNotice={setNotice} connectLinkedIn={connectLinkedIn} />}
        {active === "news" && <NewsView query={newsQuery} setQuery={setNewsQuery} articles={newsArticles} search={loadNews} />}
      </section>
    </main>
  );
}

function Sparkline({ values, change }: { values: number[]; change: number }) {
  if (!values.length) return <span className="sparkline-empty">—</span>;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${34 - ((value - min) / spread) * 28}`).join(" ");
  return <svg className={`sparkline ${change >= 0 ? "up" : "down"}`} viewBox="0 0 100 38" preserveAspectRatio="none" aria-label={`${change >= 0 ? "Up" : "Down"} price trend`}><polyline points={points} fill="none" vectorEffect="non-scaling-stroke" /></svg>;
}

function MarketView({ companies, onResearch, refresh }: { companies: MarketCompany[]; onResearch: (ticker: string) => void; refresh: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function refreshMarket() {
    setBusy(true);
    setError("");
    try { await refresh(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Market refresh failed"); } finally { setBusy(false); }
  }
  return <section className="market-view"><div className="market-heading"><div><p className="section-kicker">MARKET · EOD DASHBOARD</p><h2>Companies to watch</h2><p className="muted">Latest stored NSE/BSE closes, daily moves, and compact price trends. This is a discovery view, not investment advice.</p></div><div className="market-heading-actions"><span className="provenance">{companies.length ? "SUPABASE · YFINANCE" : "WAITING FOR DATA"}</span><button className="outline-button" onClick={() => void refreshMarket()} disabled={busy}>{busy ? "Loading…" : "↻ Refresh prices"}</button></div></div>{error && <div className="network-error">{error}</div>}{companies.length ? <div className="market-table">{companies.map((company) => <button className="market-row" key={company.ticker} onClick={() => onResearch(company.ticker)}><div className="market-company"><strong>{company.ticker}</strong><span>{company.name}</span></div><Sparkline values={company.series} change={company.change_percent} /><div className="market-price"><strong>₹{company.price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong><span className={company.change_percent > 0 ? "positive" : company.change_percent < 0 ? "negative" : "flat"}>{company.change_percent > 0 ? "↗" : company.change_percent < 0 ? "↘" : "→"} {company.change_percent > 0 ? "+" : ""}{company.change_percent.toFixed(2)}%</span></div></button>)}</div> : <div className="market-empty"><strong>No market rows are stored yet</strong><span>Load the latest EOD data to populate the company list and sparklines.</span><button className="primary-button compact" onClick={() => void refreshMarket()} disabled={busy}>{busy ? "Loading prices…" : "Load latest prices"}</button></div>}</section>;
}

const chatPrompts = [
  "What are the most important developments in my portfolio today?",
  "Why did RELIANCE volume spike?",
  "Compare the last four quarters of revenue for TCS",
  "What did management promise in the last earnings call?",
  "Did the company achieve its guided growth?",
  "What are the biggest risks disclosed in the annual report?",
  "How reliable is the company's cash conversion?",
  "What does management say about demand and margins?",
];

function AskFinn({ messages, busy, onAsk }: { messages: ChatMessage[]; busy: boolean; onAsk: (question: string, ticker?: string) => void }) {
  const [question, setQuestion] = useState("");
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;
    onAsk(question);
    setQuestion("");
  }
  return <section className="ask-view"><div className="ask-heading"><div><p className="section-kicker">AI · PRIMARY-SOURCE ASSISTANT</p><h2>Ask FINN</h2><p className="muted">Ask about your portfolio or a supported company. Answers use annual reports and earnings-call transcripts only.</p></div><span className="provenance">GEMINI · GROUNDED</span></div>{messages.length === 0 ? <div className="prompt-grid">{chatPrompts.map((prompt) => <button key={prompt} className="prompt-card" onClick={() => onAsk(prompt)}>{prompt}</button>)}</div> : <div className="chat-thread">{messages.map((message, index) => <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}><span className="chat-role">{message.role === "user" ? "YOU" : "FINN"}</span><p>{message.text}</p>{message.sources?.length ? <div className="chat-sources">{message.sources.map((source) => source.url ? <a key={`${source.label}-${source.page}`} href={source.url} target="_blank" rel="noreferrer">{source.label}{source.page ? ` · ${source.page}` : ""} ↗</a> : <span key={`${source.label}-${source.page}`}>{source.label}{source.page ? ` · ${source.page}` : ""}</span>)}</div> : null}</article>)}</div>}<form className="chat-input" onSubmit={submit}><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about a company, filing, guidance, or risk…" aria-label="Ask FINN a question" /><button className="primary-button" type="submit" disabled={busy || !question.trim()}>{busy ? "Thinking…" : "Ask"}</button></form><p className="chat-disclaimer">FINN will say when the loaded primary sources do not support an answer. News is contextual and is not used as Pull evidence.</p></section>;
}

function Today({ alerts, opportunities, highPriorityCount, selectedAlert, setSelectedAlert, trackedCompanies, onResearch, onAddCompany, refreshMarket }: { alerts: AlertItem[]; opportunities: AlertItem[]; highPriorityCount: number; selectedAlert: AlertItem | null; setSelectedAlert: (item: AlertItem | null) => void; trackedCompanies: PortfolioCompany[]; onResearch: (ticker: string) => void; onAddCompany: (query: string) => Promise<{ company: PortfolioCompany; research_ready: boolean; message: string }>; refreshMarket: () => Promise<void> }) {
  const detailRef = useRef<HTMLDivElement | null>(null);
  const [portfolioExpanded, setPortfolioExpanded] = useState(false);
  const [showAddCompany, setShowAddCompany] = useState(false);
  const [companyQuery, setCompanyQuery] = useState("");
  const [addBusy, setAddBusy] = useState(false);
  const [addError, setAddError] = useState("");
  const liveSignalCount = alerts.length;

  useEffect(() => {
    if (!selectedAlert || window.innerWidth > 680) return;
    detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [selectedAlert]);

  async function submitCompany(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!companyQuery.trim()) return;
    setAddBusy(true);
    setAddError("");
    try {
      const result = await onAddCompany(companyQuery.trim());
      setCompanyQuery("");
      setShowAddCompany(false);
    } catch (caught) {
      setAddError(caught instanceof Error ? caught.message : "Could not add company");
    } finally {
      setAddBusy(false);
    }
  }

  return <>
    <section className="hero-row"><div><p className="section-kicker">PUSH · DISCOVERY</p><div className="hero-metric">{opportunities.length}<span>companies to look for</span></div><p className="muted">Ranked from stored NSE/BSE EOD moves <span className="live-pill"><i /> Market radar</span></p></div></section>
    <OpportunityPanel opportunities={opportunities} onResearch={onResearch} onAddCompany={onAddCompany} refreshMarket={refreshMarket} />
    <section className="stats-grid"><div className="stat-card accent"><span>Signal quality</span><strong>{liveSignalCount ? "Focused" : "Waiting"}</strong><small>{liveSignalCount} live source signal{liveSignalCount === 1 ? "" : "s"}</small></div><button className={`stat-card portfolio-stat-card ${portfolioExpanded ? "expanded" : ""}`} onClick={() => setPortfolioExpanded((current) => !current)} aria-expanded={portfolioExpanded}><span>Portfolio</span><strong>{trackedCompanies.length}</strong><small>{portfolioExpanded ? "Hide company list ↑" : "NSE / BSE names · View list ↓"}</small></button></section>
    {portfolioExpanded && <section className="portfolio-list-panel"><div className="portfolio-list-heading"><div><p className="section-kicker">TRACKED UNIVERSE</p><h3>{trackedCompanies.length} portfolio companies</h3></div><div className="portfolio-actions"><span className="muted">NSE / BSE names</span><button className="outline-button" onClick={() => { setShowAddCompany((current) => !current); setAddError(""); }}>{showAddCompany ? "Close" : "+ Add company"}</button></div></div>{showAddCompany && <form className="add-company-form" onSubmit={submitCompany}><label>Company name or NSE/BSE ticker<input value={companyQuery} onChange={(event) => setCompanyQuery(event.target.value)} placeholder="e.g. TCS or Tata Consultancy Services" required /></label><button className="primary-button compact" type="submit" disabled={addBusy}>{addBusy ? "Adding…" : "Add company"}</button></form>}{addError && <div className="network-error">{addError}</div>}<div className="portfolio-company-grid">{trackedCompanies.map((company) => <button className="portfolio-company" key={company.ticker} onClick={() => onResearch(company.ticker)}><span className="ticker-badge">{company.ticker}</span><span><strong>{company.name}</strong><small>{company.sector}</small></span><span className="chevron">›</span></button>)}</div></section>}
    <section className="workspace-grid"><div className="feed-panel"><div className="panel-heading"><div><p className="section-kicker">SIGNAL FEED</p><h2>What changed</h2><p className="muted">Primary-source updates, market signals, and contextual news.</p></div></div>{alerts.length ? <div className="alert-list">{alerts.map((item) => <div key={item.id} className={`alert-card ${selectedAlert?.id === item.id ? "selected" : ""}`} role="button" tabIndex={0} onClick={() => setSelectedAlert(item)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedAlert(item); } }}><div className={`priority-bar ${item.priority.toLowerCase()}`} /><div className="alert-main"><div className="alert-topline"><span className="tag">{item.kind}</span><span className="priority-text">{item.priority} priority</span></div><h3>{item.title}</h3><p>{item.summary}</p><div className="card-foot"><span>{item.ticker} · {item.company}</span><span className={`metric ${item.metric.tone}`}>{item.metric.label} <strong>{item.metric.value}</strong></span>{item.source.url && <a className="source-link" href={item.source.url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>Open source ↗</a>}</div></div><span className="chevron">›</span></div>)}</div> : <div className="feed-empty"><strong>No live signals yet</strong><span>Ingest an annual report or earnings-call transcript, add market data, or check GNews context to populate Today.</span></div>}</div>{selectedAlert ? <div ref={detailRef} className="detail-slot"><DetailPanel alert={selectedAlert} onResearch={onResearch} /></div> : <div ref={detailRef} className="detail-slot"><aside className="detail-panel empty-detail"><p className="section-kicker">WHY THIS SIGNAL MATTERS</p><h2>Select a live signal</h2><p className="muted">This panel will explain the impact, metric, source, and relevant network matches for the selected live update.</p></aside></div>}</section>
  </>;
}

function OpportunityPanel({ opportunities, onResearch, onAddCompany, refreshMarket }: { opportunities: AlertItem[]; onResearch: (ticker: string) => void; onAddCompany: (query: string) => Promise<{ company: PortfolioCompany; research_ready: boolean; message: string }>; refreshMarket: () => Promise<void> }) {
  const [addingTicker, setAddingTicker] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  async function addCompany(ticker: string) {
    setAddingTicker(ticker);
    setError("");
    try {
      await onAddCompany(ticker);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Company could not be added");
    } finally {
      setAddingTicker(null);
    }
  }

  async function loadMarket() {
    setRefreshing(true);
    setError("");
    try {
      await refreshMarket();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Market data could not be loaded");
    } finally {
      setRefreshing(false);
    }
  }

  return <section className="opportunity-panel"><div className="panel-heading"><div><p className="section-kicker">COMPANIES TO LOOK FOR</p><h2>What deserves a closer look?</h2><p className="muted">Top EOD movers from the tracked NSE/BSE universe. Every candidate needs primary-source verification.</p></div><div className="opportunity-heading-actions"><span className="provenance">MARKET RADAR</span><button className="outline-button" onClick={() => void loadMarket()} disabled={refreshing}>{refreshing ? "Loading…" : "↻ Refresh prices"}</button></div></div>{error && <div className="alert-settings-error">{error}</div>}{opportunities.length ? <div className="opportunity-grid">{opportunities.map((item) => <article className="opportunity-card" key={item.id}><div className="opportunity-topline"><span className="tag">{item.kind}</span><span className="priority-text">{item.priority} priority</span></div><h3>{item.company} <small>{item.ticker}</small></h3><p>{item.summary}</p><div className="opportunity-metric"><span>{item.metric.label}</span><strong className={item.metric.tone}>{item.metric.value}</strong></div><div className="opportunity-actions"><button className="primary-button compact" onClick={() => onResearch(item.ticker)}>Research</button><button className="outline-button" onClick={() => void addCompany(item.ticker)} disabled={addingTicker === item.ticker}>{addingTicker === item.ticker ? "Adding…" : "Add to portfolio"}</button></div></article>)}</div> : <div className="opportunity-empty"><strong>No market candidates yet</strong><span>Load the latest EOD prices to populate this radar.</span><button className="primary-button compact" onClick={() => void loadMarket()} disabled={refreshing}>{refreshing ? "Loading prices…" : "Load latest prices"}</button></div>}</section>;
}

function DetailPanel({ alert, onResearch }: { alert: AlertItem; onResearch: (ticker: string) => void }) {
  return <aside className="detail-panel"><div className="panel-heading"><div><p className="section-kicker">WHY THIS SIGNAL MATTERS</p><h2>{alert.ticker}</h2></div><span className="detail-kind">{alert.kind}</span></div><p className="detail-summary">{alert.impact}</p><div className="detail-metric"><span>{alert.metric.label}</span><strong>{alert.metric.value}</strong></div><div className="evidence-box"><div className="evidence-title"><span className="verified-icon">✓</span><strong>Evidence trail</strong></div><p>{alert.source.label} · {alert.source.page ?? "end-of-day"}</p><span className="provenance">{alert.source.provenance}</span></div><div className="network-block"><div className="block-heading"><div><p className="section-kicker">NETWORK SIGNAL</p><h3>Who can help?</h3></div><span className="network-icon">⌁</span></div>{alert.network.slice(0, 2).map((person) => <NetworkRow key={person.name} person={person} />)}</div><button className="primary-button" onClick={() => onResearch(alert.ticker)}>Research {alert.ticker} <span>→</span></button></aside>;
}

function NetworkRow({ person }: { person: NetworkMatch }) {
  return <div className="network-row"><span className="avatar person-avatar">{person.name.split(" ").map((part) => part[0]).join("")}</span><span className="network-copy"><strong>{person.name}</strong><small>{person.role}</small><em>{person.evidence} · {person.score}% relevance{person.source ? ` · ${person.source}` : ""}</em></span></div>;
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
  const status = section.status.toLowerCase();
  if (status === "synthetic demo") return <div className="citation missing">Synthetic demo · replace with extracted evidence</div>;
  if (status === "interpreted") return <div className="citation derived">AI interpretation based on trusted sources</div>;
  if (sources.length) {
    const source = sources[0];
    const label = source.label.replace(/\.pdf$/i, "");
    const footer = `Evidence · ${label}${source.page ? ` · ${source.page}` : ""}`;
    return source.url ? <a className="citation" href={source.url} target="_blank" rel="noreferrer">{footer} ↗</a> : <div className="citation">{footer}</div>;
  }
  if (status === "unavailable") return null;
  return <div className="citation missing">No trusted evidence loaded</div>;
}

function ResearchChart({ section }: { section: ResearchSection }) {
  const metrics = (section.metrics ?? []).map((metric) => ({ ...metric, number: Number((metric.value.replace(/,/g, "").match(/-?\d+(?:\.\d+)?/) ?? [""])[0]) })).filter((metric) => Number.isFinite(metric.number));
  if (metrics.length < 2) return <div className="chart-empty">Chart appears when comparable figures are present in the loaded source.</div>;
  const max = Math.max(...metrics.map((metric) => Math.abs(metric.number)), 1);
  if (section.label.toLowerCase() === "financial snapshot") {
    return <div className="financial-chart" aria-label="Financial snapshot comparison">{metrics.slice(0, 4).map((metric) => <div className="financial-row" key={`${metric.label}-${metric.value}`}><small>{metric.label}</small><div className="financial-track"><span style={{ width: `${Math.max(8, Math.round(Math.abs(metric.number) / max * 100))}%` }} /></div><strong>{metric.value}</strong></div>)}</div>;
  }
  if (section.label.toLowerCase() === "balance sheet") {
    return <div className="balance-chart" aria-label="Balance sheet metric comparison">{metrics.slice(0, 4).map((metric) => <div className="balance-bar" key={`${metric.label}-${metric.value}`}><div className="balance-bar-track"><span style={{ height: `${Math.max(12, Math.round(Math.abs(metric.number) / max * 100))}%` }} /></div><strong>{metric.value}</strong><small>{metric.label}</small></div>)}</div>;
  }
  const plot = metrics.slice(0, 6).map((metric, index, values) => ({ metric, x: 4 + (index / Math.max(values.length - 1, 1)) * 92, y: 92 - (Math.abs(metric.number) / max) * 72 }));
  return <div className="trajectory-chart" aria-label="Trajectory metric trend"><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img"><polyline points={plot.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="currentColor" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />{plot.map((point) => <ellipse className="trajectory-point" key={`${point.metric.label}-${point.metric.value}`} cx={point.x} cy={point.y} rx="0.8" ry="3.5" />)}</svg><div className="chart-labels">{plot.map((point) => <span key={`${point.metric.label}-${point.metric.value}`}><strong>{point.metric.value}</strong><small>{point.metric.label}</small></span>)}</div><small className="chart-hint">Reported values are shown below the graph.</small></div>;
}

function ResearchCard({ section }: { section: ResearchSection }) {
  const chartable = section.label === "Financial snapshot" || section.label === "Trajectory" || section.label === "Balance sheet";
  return <article className={`research-card ${section.variant ?? "insight"}`}><div className="card-topline"><span className="section-kicker">{section.label}</span><span className={`status-label ${section.status.toLowerCase().replace(" ", "-")}`}>{section.status}</span></div><p>{section.text}</p>{chartable && section.metrics?.length ? <ResearchChart section={section} /> : null}{section.metrics?.length ? <div className="metric-strip">{section.metrics.slice(0, 4).map((metric) => <div className={`research-metric ${metric.trend ?? "neutral"}`} key={`${metric.label}-${metric.value}`}><small>{metric.label}</small><strong>{metric.value}</strong><em>{metric.trend && metric.trend !== "neutral" ? metric.trend : "reported"}</em></div>)}</div> : null}<ResearchCitations section={section} /></article>;
}

function CaseCard({ section }: { section: ResearchSection }) {
  return <article className={`case-card ${section.tone ?? "bull"}`}><div className="case-card-head"><span className="case-marker">{section.tone === "bear" ? "↓" : "↑"}</span><div><p className="section-kicker">{section.label}</p><span className="case-caption">Scenario interpretation</span></div></div><p>{section.text}</p><ResearchCitations section={section} /></article>;
}

function FinancialSnapshotTable({ section }: { section: ResearchSection }) {
  const metrics = section.metrics ?? [];
  return <div className="financial-snapshot-table"><div className="financial-table-head"><span>Metric</span><span>Reported</span><span>Direction</span></div>{metrics.length ? metrics.slice(0, 6).map((metric) => <div className="financial-table-row" key={`${metric.label}-${metric.value}`}><div><strong>{metric.label}</strong><small>Source-reported figure</small></div><strong>{metric.value}</strong><span className={metric.trend === "up" ? "positive" : metric.trend === "down" ? "negative" : "flat"}>{metric.trend === "up" ? "↗ Up" : metric.trend === "down" ? "↘ Down" : "→ Reported"}</span></div>) : <div className="financial-table-empty">No comparable financial figures were extracted from the loaded source.</div>}</div>;
}

function ResearchView({ ticker, setTicker, research, loadResearch, marketCompany, trackedCompanies, onBack, onNetwork }: { ticker: string; setTicker: (value: string) => void; research: Research; loadResearch: () => void; marketCompany?: MarketCompany; trackedCompanies: PortfolioCompany[]; onBack: () => void; onNetwork: (matches: NetworkMatch[]) => void }) {
  const isLive = research.provenance?.startsWith("Gemini interpretation");
  const summary = research.sections.find((section) => section.variant === "summary" || section.label.toLowerCase() === "research summary") ?? { label: "Research summary", text: research.headline, status: "Interpreted", source: null, variant: "summary" as const };
  const rawInsights = research.sections.filter((section) => section.variant === "insight" || (!section.variant && !section.label.toLowerCase().includes("evidence") && !section.label.toLowerCase().includes("bull")));
  const insights = REQUIRED_INSIGHTS.map((required) => rawInsights.find((section) => required.aliases.includes(section.label.toLowerCase())))
    .filter((section): section is ResearchSection => section !== undefined && section.status.toLowerCase() !== "unavailable");
  let cases = research.sections.filter((section) => section.variant === "case");
  const legacyCase = research.sections.find((section) => section.label.toLowerCase().includes("bull / bear"));
  if (!cases.length && legacyCase) cases = [{ ...legacyCase, label: "Bull case", tone: "bull", variant: "case" }, { ...legacyCase, label: "Bear case", tone: "bear", variant: "case" }];
  const financialSnapshot = insights.find((section) => section.label.toLowerCase() === "financial snapshot");
  const otherInsights = insights.filter((section) => section.label.toLowerCase() !== "financial snapshot");
  const inPortfolio = trackedCompanies.some((company) => company.ticker === research.ticker);
  const companySector = marketCompany?.sector ?? "Public company";
  const jumpTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return <section className="research-view"><div className="research-header"><div><button className="back-link" onClick={() => setTicker("")}>← All companies</button><p className="section-kicker">PULL · PRIMARY-SOURCE RESEARCH</p><h2>Read the company, then test the story</h2><p className="muted">Annual reports and earnings-call transcripts only. News remains contextual and is excluded from this view.</p></div><div className="ticker-search"><input value={ticker} onChange={(event) => setTicker(event.target.value)} onKeyDown={(event) => event.key === "Enter" && loadResearch()} placeholder="NSE ticker" aria-label="NSE ticker" /><button onClick={loadResearch}>Research</button></div></div>{research.available ? <><div className="pull-company-header"><div><h1>{research.company}</h1><p>{research.ticker} · {companySector} · consolidated figures</p><div className="pull-quote">{marketCompany ? <><strong>₹{marketCompany.price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong><span className={marketCompany.change_percent >= 0 ? "positive" : "negative"}>{marketCompany.change_percent >= 0 ? "↗ +" : "↘ "}{marketCompany.change_percent.toFixed(2)}%</span><small>close {marketCompany.trading_date}</small></> : <small>Price data unavailable · run EOD market ingestion</small>}</div></div><span className="portfolio-state">{inPortfolio ? "✓ In portfolio" : "＋ Add to portfolio"}</span></div><div className="pull-metric-strip"><div><span>Market data</span><strong>{marketCompany ? "Available" : "Unavailable"}</strong></div><div><span>Primary sources</span><strong>{research.disclosure.match(/\d+/)?.[0] ?? "—"}</strong></div><div><span>Model</span><strong>{isLive ? "Gemini" : "Unavailable"}</strong></div><div><span>Evidence state</span><strong>{research.available ? "Loaded" : "Missing"}</strong></div></div><div className="research-tabs">{[["financial-snapshot", "Snapshot"], ["trajectory", "Trajectory"], ["guidance", "Promises"], ["cases", "Bull / bear"], ["network", "Who to call"], ["balance-sheet", "Balance sheet"], ["cash-quality", "Cash quality"]].map(([id, label]) => <button key={id} onClick={() => jumpTo(id)}>{label}</button>)}</div><div className="reading-panel"><div><h3>Read the annual report and the latest earnings calls</h3><p>Builds a cited summary, financial snapshots, trajectory, guidance, and a bull/bear case from the documents loaded for {research.ticker}.</p></div><button className="primary-button" onClick={loadResearch}>Start reading</button></div><div className="source-note">Figures and summaries come from the trusted primary-source documents loaded for this company, such as its annual report or earnings-call transcript. News is contextual only and is not used in Pull analysis.</div>{financialSnapshot && <section id="financial-snapshot" className="pull-section"><div className="pull-section-heading"><span>▸</span><div><p className="section-kicker">FINANCIAL SNAPSHOT</p><h3>Reported headline figures</h3></div><small>Source-reported values</small></div><article className="pull-table-card"><p>{financialSnapshot.text}</p><FinancialSnapshotTable section={financialSnapshot} /><ResearchCitations section={financialSnapshot} /></article></section>}<section id="summary" className="pull-section"><div className="pull-section-heading"><span>▸</span><div><p className="section-kicker">SUMMARY</p><h3>What matters first</h3></div></div><article className="summary-card"><div className="summary-card-top"><div><p className="section-kicker">RESEARCH SUMMARY</p><h3>{summary.text}</h3></div><span className="summary-icon">✦</span></div><ResearchCitations section={summary} /></article></section><div className="research-grid insight-grid">{otherInsights.map((section) => <div id={section.label.toLowerCase().replace(/[^a-z]+/g, "-")} key={section.label}><ResearchCard section={section} /></div>)}</div>{cases.length ? <section id="cases" className="pull-section"><div className="research-subheading case-heading"><div><p className="section-kicker">SCENARIO FRAME</p><h3>Bull versus bear</h3></div><span className="muted">Interpretation, not a recommendation</span></div><div className="case-grid">{cases.map((section) => <CaseCard section={section} key={`${section.label}-${section.tone}`} />)}</div></section> : null}<section id="network" className="research-network"><div><p className="section-kicker">NETWORK CONTEXT</p><h3>Top contacts for {research.ticker}</h3><p className="muted">Showing the top 3 relevance-ranked matches. Open network view for the full list.</p></div><div className="research-network-list">{research.network.slice(0, 3).map((person) => <NetworkRow key={person.name} person={person} />)}</div><button className="outline-button" onClick={() => onNetwork(research.network)}>Open all network matches →</button></section></> : <div className="empty-state"><span className="empty-icon">⌕</span><h3>Evidence unavailable</h3><p>{research.disclosure}</p><p>Try again in a few seconds if Gemini is temporarily busy.</p><button className="outline-button" onClick={loadResearch}>Try again</button></div>}</section>;
}

function NetworkView({ ticker, setTicker, query, setQuery, matches, search, contacts, refreshContacts, onNotice, connectLinkedIn }: { ticker: string; setTicker: (value: string) => void; query: string; setQuery: (value: string) => void; matches: NetworkMatch[]; search: () => void; contacts: NetworkContact[]; refreshContacts: () => Promise<void>; onNotice: (value: string) => void; connectLinkedIn: () => Promise<void> }) {
  const [showManual, setShowManual] = useState(false);
  const [manual, setManual] = useState({ name: "", role: "", company: "", sector: "", skills: "", linkedin_url: "", relationship: "", notes: "" });
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvPreview, setCsvPreview] = useState<CsvPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function updateManual(field: keyof typeof manual, value: string) {
    setManual((current) => ({ ...current, [field]: value }));
  }

  async function previewCsv(file: File | undefined) {
    if (!file) return;
    setCsvFile(file);
    setError("");
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    try {
      const response = await apiFetch("/network/import/csv/preview", { method: "POST", body });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not preview CSV");
      setCsvPreview(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not preview CSV");
    } finally {
      setBusy(false);
    }
  }

  async function importCsv() {
    if (!csvFile) return;
    const body = new FormData();
    body.append("file", csvFile);
    setBusy(true);
    setError("");
    try {
      const response = await apiFetch("/network/import/csv", { method: "POST", body });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail?.message ?? result.detail ?? "Could not import CSV");
      await refreshContacts();
      await search();
      setCsvFile(null);
      setCsvPreview(null);
      onNotice(`${result.inserted} contact${result.inserted === 1 ? "" : "s"} imported from CSV.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not import CSV");
    } finally {
      setBusy(false);
    }
  }

  async function addManual(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const payload = { ...manual, skills: manual.skills.split(",").map((item) => item.trim()).filter(Boolean) };
    try {
      const response = await apiFetch("/network/people", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not save contact");
      await refreshContacts();
      await search();
      setManual({ name: "", role: "", company: "", sector: "", skills: "", linkedin_url: "", relationship: "", notes: "" });
      setShowManual(false);
      onNotice("Manual contact saved to your network.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save contact");
    } finally {
      setBusy(false);
    }
  }

  function downloadTemplate() {
    const csv = "name,role,company,sector,skills,linkedin_url,relationship,notes\nNeha Rao,Technology executive,Example Corp,Technology,delivery;cloud,https://linkedin.com/in/example,Former colleague,Worked together\n";
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "finn-network-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return <section className="network-view"><div className="research-header"><div><p className="section-kicker">NETWORK · YOUR CONTEXT</p><h2>Who should I call?</h2><p className="muted">Add people you trust, then let FINN rank relevant context alongside Push and Pull research.</p></div></div><div className="network-source-grid"><article className="network-source-card"><span className="source-icon">↑</span><div><h3>Import CSV</h3><p>Bring in a contact list with a preview before anything is saved.</p></div><div className="source-actions"><label className="outline-button file-button">Choose CSV<input type="file" accept=".csv,text/csv" onChange={(event) => void previewCsv(event.target.files?.[0])} /></label><button className="text-button" onClick={downloadTemplate}>Download template</button></div></article><article className="network-source-card"><span className="source-icon">+</span><div><h3>Add manually</h3><p>Feed FINN one useful relationship at a time.</p></div><button className="outline-button" onClick={() => setShowManual((current) => !current)}>{showManual ? "Close form" : "Add contact"}</button></article><article className="network-source-card future"><span className="source-icon">in</span><div><h3>LinkedIn</h3><p>Import approved first-degree connections through OAuth.</p></div><button className="outline-button linkedin-button" onClick={() => void connectLinkedIn()}>Connect LinkedIn</button><span className="coming-soon">OPTIONAL OAUTH</span></article></div>{csvPreview ? <div className="csv-preview"><div className="csv-preview-top"><div><p className="section-kicker">CSV PREVIEW</p><h3>{csvPreview.filename}</h3><span>{csvPreview.valid_rows.length} valid of {csvPreview.row_count} rows</span></div><button className="primary-button compact" onClick={() => void importCsv()} disabled={busy || !csvPreview.valid_rows.length}>{busy ? "Importing…" : "Import valid contacts"}</button></div>{csvPreview.errors.length ? <div className="csv-errors">{csvPreview.errors.slice(0, 5).map((item) => <span key={item}>⚠ {item}</span>)}</div> : <p className="csv-ok">✓ All rows passed validation.</p>}</div> : null}{showManual ? <form className="manual-form" onSubmit={addManual}><div className="form-heading"><div><p className="section-kicker">MANUAL CONTACT</p><h3>Add someone useful</h3></div><span className="muted">Required: name</span></div><div className="manual-fields"><label>Name<input required value={manual.name} onChange={(event) => updateManual("name", event.target.value)} placeholder="Full name" /></label><label>Role<input value={manual.role} onChange={(event) => updateManual("role", event.target.value)} placeholder="e.g. CFO, sector analyst" /></label><label>Company<input value={manual.company} onChange={(event) => updateManual("company", event.target.value)} placeholder="Company or employer" /></label><label>Sector<input value={manual.sector} onChange={(event) => updateManual("sector", event.target.value)} placeholder="Technology, banking…" /></label><label>Skills<input value={manual.skills} onChange={(event) => updateManual("skills", event.target.value)} placeholder="Separate skills with commas" /></label><label>LinkedIn URL<input value={manual.linkedin_url} onChange={(event) => updateManual("linkedin_url", event.target.value)} placeholder="Optional" /></label><label>Relationship<input value={manual.relationship} onChange={(event) => updateManual("relationship", event.target.value)} placeholder="How do you know them?" /></label><label className="wide-field">Notes<textarea value={manual.notes} onChange={(event) => updateManual("notes", event.target.value)} placeholder="Why might this person help?" /></label></div><button className="primary-button compact" type="submit" disabled={busy}>{busy ? "Saving…" : "Save contact"}</button></form> : null}{error ? <div className="network-error">{error}</div> : null}<div className="network-search"><div><label>Company or ticker</label><input value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="TCS" /></div><div><label>What do you need to understand?</label><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. delivery economics" /></div><button className="primary-button" onClick={search}>Find context <span>→</span></button></div><div className="network-result-heading"><div><p className="section-kicker">MATCHES FOR {ticker.toUpperCase()}</p><h3>People who may help</h3></div><span className="provenance">{contacts.length ? `${contacts.length} imported contact${contacts.length === 1 ? "" : "s"}` : "Synthetic fallback"}</span></div><div className="network-results">{matches.length ? matches.map((person) => <article className="large-network-card" key={person.personId ?? person.name}><span className="avatar person-avatar large">{person.name.split(" ").map((part) => part[0]).join("")}</span><div className="large-network-copy"><div className="card-topline"><span className="tag">{person.evidence}</span><strong>{person.score}% relevance</strong></div><h3>{person.name}</h3><p>{person.role}</p><div className="reason-box"><strong>Why this match</strong><span>{person.reason}</span></div><div className="match-meta"><span>{person.source ?? "Synthetic demo"}</span><small>{person.caveat}</small></div></div></article>) : <div className="empty-state small"><h3>No relevant match found</h3><p>Import or add a contact, then search by company and question.</p></div>}</div></section>;
}

function NewsView({ query, setQuery, articles, search }: { query: string; setQuery: (value: string) => void; articles: NewsArticle[]; search: () => void }) {
  return <section className="news-view"><div className="research-header"><div><p className="section-kicker">NEWS · CONTEXT ONLY</p><h2>What is being said?</h2><p className="muted">GNews articles help you monitor context. They are never used as evidence for Pull analysis.</p></div></div><div className="news-search"><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && search()} placeholder="Company, sector, or theme" aria-label="News search" /><button className="primary-button" onClick={search}>Search news <span>→</span></button></div>{articles.length ? <div className="news-list">{articles.map((article) => <article className="news-card" key={article.id ?? article.url ?? article.title}><div className="card-topline"><span className="tag">{article.source?.name ?? "News source"}</span></div><h3>{article.title}</h3>{article.description && <p>{article.description}</p>}<div className="news-foot"><span>{article.publishedAt ? new Date(article.publishedAt).toLocaleString() : "Publication time unavailable"}</span>{article.url && <a href={article.url} target="_blank" rel="noreferrer">Open source ↗</a>}</div></article>)}</div> : <div className="empty-state"><span className="empty-icon">✦</span><h3>Search for context</h3><p>Enter a company or theme, then search GNews through the backend.</p><p className="muted">The API key stays server-side; news is excluded from Pull.</p></div>}</section>;
}
