import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Category = 'auto' | 'manual' | 'critical';
type Action = { actionName: string; description: string; category: Category; stepGroups: { steps: string[]; actionableDeeplink: { deeplink: string; description: string } | null; validationDeeplink: { deeplink: string; key: string } | null }[] };
type Goal = { goal: string; title: string; score: number; actions: Action[] };
type OfficialResponse = { contexts: Goal[] };
type SelectionAction = { id: string; name: string; operation: string; source_ids: string[]; catalog_id: string | null; applicability: 'applicable' | 'not applicable' | 'needs confirmation'; condition_reasons: string[] };
type Selection = { id: string; title: string; feature_area: string; disposition: string; reason: string; actions: SelectionAction[] };
type PreviewResponse = { response: OfficialResponse; preview: { procedures: Selection[]; facts: Record<string, boolean | null>; fact_provenance: Record<string, string>; source_limitations: string[] }; evidence: { article_hash: string; source_blocks: Record<string, { start: number; end: number; text: string }>; catalog: Record<string, { description: string; deeplink: string }>; compilation_ledger: { source_id: string; disposition: string; reason: string }[] }; trace: { request_id: string; cache_status: string; processing_time_ms: string; stages: Record<string, string>; stage_timings_ms: Record<string, number> } };
type Sample = { query: string; title: string; content: string };
type DevelopmentSample = Sample & { provenance: string };
type Tab = 'guide' | 'official' | 'evidence';

const FACTS: { key: string; label: string }[] = [
  { key: 'has_protector', label: 'Screen protector present' },
  { key: 'retain_protector', label: 'Keep the protector' },
  { key: 'touch_sensitivity_enabled', label: 'Touch sensitivity enabled' },
  { key: 'screen_visible', label: 'Screen visible' },
  { key: 'touch_working', label: 'Touch works' },
  { key: 'inner_screen_visible', label: 'Inner display visible' },
  { key: 'cover_screen_visible', label: 'Cover display visible' },
  { key: 'inner_touch_working', label: 'Inner display touch works' },
  { key: 'cover_touch_working', label: 'Cover display touch works' },
  { key: 'alternate_input_available', label: 'Mouse or keyboard available' },
  { key: 'hdmi_compatible', label: 'HDMI output supported' },
  { key: 'backup_complete', label: 'Backup complete' },
  { key: 'prior_steps_failed', label: 'Prior steps failed' },
];

function App() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [developmentSample, setDevelopmentSample] = useState<DevelopmentSample | null>(null);
  const [selectedSample, setSelectedSample] = useState('');
  const [query, setQuery] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [facts, setFacts] = useState<Record<string, boolean | null>>({});
  const [result, setResult] = useState<PreviewResponse | null>(null);
  const [tab, setTab] = useState<Tab>('guide');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const demoStarted = useRef(false);

  useEffect(() => {
    void Promise.all([
      fetch('/health').then((response) => setReady(response.ok)).catch(() => setReady(false)),
      fetch('/api/samples').then((response) => response.ok ? response.json() as Promise<Sample[]> : []).then(setSamples).catch(() => setSamples([])),
      fetch('/api/development-sample').then((response) => response.ok ? response.json() as Promise<DevelopmentSample> : null).then(setDevelopmentSample).catch(() => setDevelopmentSample(null)),
    ]);
  }, []);

  useEffect(() => {
    const mode = new URLSearchParams(window.location.search).get('demo');
    if (!mode || demoStarted.current) return;
    const sample = mode.startsWith('mixed') ? samples[2] : mode.startsWith('touch') ? samples[18] : mode.startsWith('fold') ? developmentSample : null;
    if (!sample) return;
    demoStarted.current = true;
    setSelectedSample(mode.startsWith('fold') ? '' : mode.startsWith('mixed') ? '2' : '18');
    setQuery(sample.query);
    setTitle(sample.title);
    setContent(sample.content);
    void fetch('/v1/preview', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: sample.query, siis_response: { title: sample.title, content: sample.content } }),
    }).then(async (response) => {
      if (!response.ok) throw new Error(`Demo request failed (${response.status})`);
      setResult(await response.json() as PreviewResponse);
      setTab(mode.endsWith('evidence') ? 'evidence' : mode.endsWith('official') ? 'official' : 'guide');
    }).catch((caught: unknown) => setError(caught instanceof Error ? caught.message : 'Demo request failed.'));
  }, [samples, developmentSample]);

  const included = useMemo(() => result?.preview.procedures.filter((item) => item.disposition === 'included') ?? [], [result]);
  const excluded = useMemo(() => result?.preview.procedures.filter((item) => item.disposition !== 'included') ?? [], [result]);
  const actionCount = result?.response.contexts.reduce((count, goal) => count + goal.actions.length, 0) ?? 0;

  function loadSample(index: number) {
    const sample = samples[index];
    if (!sample) return;
    setSelectedSample(String(index));
    setQuery(sample.query);
    setTitle(sample.title);
    setContent(sample.content);
    setFacts({});
    setResult(null);
    setError('');
  }

  function loadDevelopmentSample() {
    if (!developmentSample) return;
    setSelectedSample('');
    setQuery(developmentSample.query);
    setTitle(developmentSample.title);
    setContent(developmentSample.content);
    setFacts({});
    setResult(null);
    setError('');
  }

  async function run() {
    if (!query.trim() || !content.trim()) {
      setError('Enter a complaint and a source article to run the guide.');
      return;
    }
    setBusy(true);
    setError('');
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8500);
    try {
      const response = await fetch('/v1/preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ query, siis_response: { title, content }, facts }),
      });
      if (!response.ok) {
        const body: { detail?: string } = await response.json();
        throw new Error(body.detail || `Request failed (${response.status})`);
      }
      setResult(await response.json() as PreviewResponse);
      setTab('guide');
    } catch (caught) {
      setError(caught instanceof DOMException && caught.name === 'AbortError' ? 'The request exceeded the client time limit.' : caught instanceof Error ? caught.message : 'Unable to generate the guide.');
    } finally {
      window.clearTimeout(timeout);
      setBusy(false);
    }
  }

  async function copyResponse() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result.response, null, 2));
    } catch {
      setError('Clipboard access is unavailable in this browser.');
    }
  }

  function renderAction(action: Action, selection?: SelectionAction) {
    return <article className="action-card" key={`${action.actionName}-${selection?.id ?? ''}`}>
      <div className="action-top"><h4>{action.actionName}</h4><div className="badges"><span className={`badge ${action.category}`}>{action.category}</span>{selection && <span className={`badge state-${selection.applicability.replace(' ', '-')}`}>{selection.applicability}</span>}</div></div>
      <p className="action-description">{action.description}</p>
      {selection?.condition_reasons.map((reason, index) => <p className="condition" key={index}>Condition from source: {reason}</p>)}
      {action.stepGroups.map((group, groupIndex) => <div key={groupIndex}>
        <ol className="steps">{group.steps.map((step, index) => <li key={index}>{step}</li>)}</ol>
        <div className="link-row">{group.actionableDeeplink ? <span className="link-chip" title={group.actionableDeeplink.deeplink}>Catalog action available</span> : <span className="link-chip neutral">Manual guidance</span>}{group.validationDeeplink && <span className="link-chip neutral" title={group.validationDeeplink.key}>Validation read available</span>}</div>
      </div>)}
    </article>;
  }

  return <div className="shell">
    <header className="topbar"><div className="brand"><span className="brand-symbol">P</span><div><strong>PRISM</strong><small>Guided Troubleshooting Studio</small></div></div><div className="topbar-right"><span className={`health-dot ${ready ? 'online' : ''}`} />{ready ? 'Engine ready' : 'Engine unavailable'}<span className="topbar-divider" /><span>Theme 02</span></div></header>
    <main className="workspace">
      <section className="intro"><div><p className="eyebrow">SOURCE-GROUNDED SUPPORT</p><h1>From a device complaint to a guide you can inspect.</h1><p>Compile the complete support article, review the relevant path, and see exactly which conditions and catalog links were used.</p></div><div className="intro-mark">02<span> / PRISM</span></div></section>
      <div className="grid">
        <section className="panel input-panel" aria-label="Request input"><div className="panel-heading"><div><span className="section-index">01</span><h2>Input</h2></div><span className="muted">Your request + SIIS source</span></div>
          <div className="quick-cases"><span>Try a case</span><button type="button" onClick={() => loadSample(2)} disabled={!samples[2]}>Mixed black-screen article</button><button type="button" onClick={() => loadSample(18)} disabled={!samples[18]}>Touch sensitivity branches</button><button type="button" onClick={loadDevelopmentSample} disabled={!developmentSample}>Foldable facts · synthetic</button></div>
          <label htmlFor="sample">Official sample</label><select id="sample" value={selectedSample} onChange={(event) => loadSample(Number(event.target.value))}><option value="" disabled>Select one of 20 queries</option>{samples.map((sample, index) => <option key={index} value={index}>{String(index + 1).padStart(2, '0')} · {sample.title}</option>)}</select>
          <label htmlFor="query">Customer complaint</label><textarea id="query" className="query-field" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Describe the device issue in your own words..." />
          <label htmlFor="title">Source article title</label><input id="title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Article title" />
          <label htmlFor="content">Source article content</label><textarea id="content" className="source-field" value={content} onChange={(event) => setContent(event.target.value)} placeholder="Paste the complete SIIS article here..." />
          <details className="fact-panel"><summary>Preview facts <span>{Object.keys(facts).length} overrides</span></summary><p>Overrides change applicability in this preview only. Unknown restores uncertainty.</p><div className="fact-grid">{FACTS.map((fact) => <label className="fact-control" key={fact.key}>{fact.label}<select value={String(facts[fact.key] ?? 'unknown')} onChange={(event) => setFacts((current) => ({ ...current, [fact.key]: event.target.value === 'unknown' ? null : event.target.value === 'true' }))}><option value="unknown">Unknown</option><option value="true">Yes</option><option value="false">No</option></select></label>)}</div></details>
          <p className="muted">Use sample or synthetic data. Requests are saved in the server cache and may be sent to Gemini. Do not enter personal or confidential information.</p>
          <button className="run-button" onClick={() => void run()} disabled={busy}>{busy ? 'Compiling guide…' : 'Generate guided response'}<span>↗</span></button>
          {error && <div className="error" role="alert">{error}</div>}
        </section>
        <section className="panel output-panel" aria-label="Generated result"><div className="panel-heading"><div><span className="section-index">02</span><h2>Result</h2></div>{result && <button type="button" className="text-button" onClick={() => void copyResponse()}>Copy official JSON</button>}</div>
          {!result ? <div className="empty-state"><div className="empty-symbol">✦</div><h3>Your guided response appears here</h3><p>Choose an official case or paste an article, then run the pipeline. The full source stays intact in the official output.</p></div> : <>
            <div className="metric-row"><div><strong>{result.response.contexts.length}</strong><span>procedures</span></div><div><strong>{actionCount}</strong><span>actions</span></div><div><strong>{included.length}</strong><span>selected</span></div><div><strong>{result.trace.processing_time_ms}</strong><span>ms backend</span></div></div>
            <div className="trace-line"><span>Cache: <b>{result.trace.cache_status.replace('_', ' ')}</b></span><span>Request {result.trace.request_id.slice(0, 8)}</span></div>
            <nav className="tabs" aria-label="Result views">{(['guide', 'official', 'evidence'] as Tab[]).map((name) => <button key={name} type="button" className={tab === name ? 'active' : ''} onClick={() => setTab(name)}>{name === 'guide' ? 'Selected guide' : name === 'official' ? 'Full official output' : 'Evidence & trace'}</button>)}</nav>
            <div className="result-scroll">
              {tab === 'guide' && <>{result.preview.source_limitations.map((limit) => <div className="notice" key={limit}>{limit}</div>)}{included.map((selection) => { const index = result.preview.procedures.indexOf(selection); const goal = result.response.contexts[index]; return <section className="procedure" key={selection.id}><div className="procedure-head"><span>{selection.id.toUpperCase()} · {selection.feature_area}</span><h3>{goal?.title ?? selection.title}</h3><p>{selection.reason}</p></div>{selection.actions.map((action, actionIndex) => goal?.actions[actionIndex] && renderAction(goal.actions[actionIndex], action))}</section>; })}{included.length === 0 && <p className="muted empty-copy">No source procedure was selected for this complaint.</p>}</>}
              {tab === 'official' && <><div className="view-explainer">All source-backed procedures remain in this API response, including those excluded from the selected preview.</div>{result.response.contexts.map((goal, index) => <section className="procedure" key={index}><div className="procedure-head"><span>CONTEXT {String(index + 1).padStart(2, '0')} · RELEVANCE {goal.score.toFixed(2)}</span><h3>{goal.title}</h3><p>{goal.goal}</p></div>{goal.actions.map((action) => renderAction(action))}</section>)}</>}
              {tab === 'evidence' && <><div className="view-explainer">Source references and catalog choices are from this request. A validation read is not proof that a setting changed on a device.</div><h3 className="evidence-title">Selection ledger</h3>{excluded.map((item) => <div className="evidence-row" key={item.id}><strong>{item.title}</strong><span>{item.disposition}</span><small>{item.reason}</small></div>)}{excluded.length === 0 && <p className="muted">No off-topic procedures were excluded.</p>}<h3 className="evidence-title">Selected source blocks</h3>{Object.entries(result.evidence.source_blocks).map(([id, block]) => <div className="source-block" key={id}><span>{id} · characters {block.start}–{block.end}</span><p>{block.text}</p></div>)}<h3 className="evidence-title">Catalog entries</h3>{Object.entries(result.evidence.catalog).map(([id, item]) => <div className="evidence-row" key={id}><strong>{id}</strong><small>{item.description}</small></div>)}<h3 className="evidence-title">Stage trace</h3><div className="trace-grid">{Object.entries(result.trace.stages).map(([stage, state]) => <div key={stage}><span>{stage}</span><strong>{state}</strong></div>)}{Object.entries(result.trace.stage_timings_ms).map(([stage, duration]) => <div key={`${stage}-time`}><span>{stage}</span><strong>{duration.toFixed(2)} ms</strong></div>)}</div></>}
            </div>
          </>}
        </section>
      </div>
      <footer>PRISM · Theme 02 <span>Source-backed actions. Explicit unknowns. Inspectable decisions.</span></footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
