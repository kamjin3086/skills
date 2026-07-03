import { useEffect, useMemo, useState } from "react";

const API_BASE = "";

function defaultValue(field) {
  if (field.default !== undefined) return field.default;
  if (field.type === "toggle") return false;
  if (field.type === "select") return field.options?.[0] ?? "";
  if (field.type === "number" || field.type === "slider") return field.min ?? 0;
  return "";
}

function ResultPreview({ outputs }) {
  if (!outputs?.length) {
    return (
      <div className="empty-result">
        <span>Result preview</span>
        <p>Your output will appear here after generation.</p>
      </div>
    );
  }

  const first = outputs[0];
  const lower = first.filename.toLowerCase();

  return (
    <div className="result-stack">
      {lower.match(/\.(mp4|webm|mov|gif)$/) ? (
        <video className="preview-media" src={`${API_BASE}${first.url}`} controls />
      ) : lower.match(/\.(png|jpg|jpeg|webp)$/) ? (
        <img className="preview-media" src={`${API_BASE}${first.url}`} alt={first.filename} />
      ) : lower.match(/\.(wav|mp3|ogg|flac)$/) ? (
        <audio src={`${API_BASE}${first.url}`} controls />
      ) : (
        <a className="download-link" href={`${API_BASE}${first.url}`} target="_blank" rel="noreferrer">
          Open {first.filename}
        </a>
      )}
      <a className="download-link" href={`${API_BASE}${first.url}`} download>
        Download {first.filename}
      </a>
    </div>
  );
}

function FieldControl({ field, value, onChange }) {
  const id = `field-${field.name}`;

  if (field.type === "textarea") {
    return (
      <label className="field" htmlFor={id}>
        <span>{field.label || field.name}</span>
        <textarea
          id={id}
          value={value}
          required={field.required}
          placeholder={field.placeholder}
          rows={5}
          onChange={(event) => onChange(field.name, event.target.value)}
        />
      </label>
    );
  }

  if (field.type === "slider") {
    return (
      <label className="field" htmlFor={id}>
        <span>{field.label || field.name}: {value}</span>
        <input
          id={id}
          type="range"
          min={field.min}
          max={field.max}
          step={field.step || 1}
          value={value}
          onChange={(event) => onChange(field.name, event.target.value)}
        />
      </label>
    );
  }

  if (field.type === "select") {
    return (
      <label className="field" htmlFor={id}>
        <span>{field.label || field.name}</span>
        <select
          id={id}
          value={value}
          required={field.required}
          onChange={(event) => onChange(field.name, event.target.value)}
        >
          {(field.options || []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (field.type === "toggle") {
    return (
      <label className="toggle-field" htmlFor={id}>
        <span>{field.label || field.name}</span>
        <input
          id={id}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(field.name, event.target.checked)}
        />
      </label>
    );
  }

  return (
    <label className="field" htmlFor={id}>
      <span>{field.label || field.name}</span>
      <input
        id={id}
        type={field.type === "number" ? "number" : "text"}
        min={field.min}
        max={field.max}
        step={field.step}
        value={value}
        required={field.required}
        placeholder={field.placeholder}
        onChange={(event) => onChange(field.name, event.target.value)}
      />
    </label>
  );
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [values, setValues] = useState({});
  const [status, setStatus] = useState({ ok: false, checking: true });
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      const configResponse = await fetch(`${API_BASE}/api/config`);
      const nextConfig = await configResponse.json();
      setConfig(nextConfig);
      setValues(Object.fromEntries((nextConfig.fields || []).map((field) => [field.name, defaultValue(field)])));

      const statusResponse = await fetch(`${API_BASE}/api/status`);
      setStatus({ ...(await statusResponse.json()), checking: false });
    }
    load().catch((loadError) => {
      setStatus({ ok: false, checking: false, error: loadError.message });
    });
  }, []);

  useEffect(() => {
    if (!job?.jobId || ["complete", "error"].includes(job.status)) return;
    const timer = setInterval(async () => {
      const response = await fetch(`${API_BASE}/api/jobs/${job.jobId}`);
      setJob(await response.json());
    }, 1200);
    return () => clearInterval(timer);
  }, [job]);

  const busy = job && !["complete", "error"].includes(job.status);
  const progressPercent = Math.round((job?.progress || 0) * 100);

  const primaryFields = useMemo(() => (config?.fields || []).filter((field) => !field.advanced), [config]);
  const advancedFields = useMemo(() => (config?.fields || []).filter((field) => field.advanced), [config]);

  function updateValue(name, value) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function generate(event) {
    event.preventDefault();
    setError("");
    setJob(null);
    try {
      const response = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Generation failed.");
      setJob({ jobId: data.jobId, status: "queued", progress: 0.05, outputs: [] });
    } catch (generateError) {
      setError(generateError.message);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <form className="control-panel" onSubmit={generate}>
          <div className="title-row">
            <div>
              <p className="eyebrow">ComfyUI workflow</p>
              <h1>{config?.appName || "Workflow App"}</h1>
            </div>
            <span className={`status-pill ${status.ok ? "online" : "offline"}`}>
              {status.checking ? "Checking" : status.ok ? "Connected" : "Offline"}
            </span>
          </div>

          {primaryFields.map((field) => (
            <FieldControl key={field.name} field={field} value={values[field.name] ?? ""} onChange={updateValue} />
          ))}

          {advancedFields.length > 0 && (
            <details className="advanced-panel">
              <summary>Advanced controls</summary>
              {advancedFields.map((field) => (
                <FieldControl key={field.name} field={field} value={values[field.name] ?? ""} onChange={updateValue} />
              ))}
            </details>
          )}

          <button className="generate-button" disabled={busy || status.checking} type="submit">
            {busy ? "Generating..." : "Generate"}
          </button>

          {!status.ok && !status.checking && (
            <p className="message error" role="alert">
              {status.error || "ComfyUI is not reachable. Start ComfyUI and refresh this page."}
            </p>
          )}
          {error && <p className="message error" role="alert">{error}</p>}
        </form>

        <section className="output-panel" aria-live="polite">
          <div className="output-header">
            <div>
              <p className="eyebrow">Output</p>
              <h2>{job?.status ? job.status : "Ready"}</h2>
            </div>
            {busy && <span className="progress-label">{progressPercent}%</span>}
          </div>
          {busy && (
            <div className="progress-track" aria-label="Generation progress">
              <div style={{ width: `${progressPercent}%` }} />
            </div>
          )}
          {job?.error && <p className="message error" role="alert">{job.error}</p>}
          <ResultPreview outputs={job?.outputs} />
        </section>
      </section>
    </main>
  );
}
