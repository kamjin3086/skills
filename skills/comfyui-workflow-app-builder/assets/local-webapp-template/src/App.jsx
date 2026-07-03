import { useEffect, useMemo, useState } from "react";

const API_BASE = "";
const STORAGE_KEY = "cwa-comfyui-workflow-app.state.v1";

function defaultValue(field) {
  if (field.default !== undefined) return field.default;
  if (field.type === "toggle") return false;
  if (field.type === "select") return field.options?.[0] ?? "";
  if (field.type === "number" || field.type === "slider") return field.min ?? 0;
  return "";
}

function slug(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

function buildDownloadUrl(output, jobId, values, appName) {
  const original = output.filename || "output.bin";
  const extension = original.includes(".") ? original.slice(original.lastIndexOf(".")) : ".bin";
  const promptHint = slug(values?.prompt) || "render";
  const appHint = slug(appName) || "comfyui";
  const unique = String(jobId || Date.now().toString(36)).slice(0, 8);
  const downloadName = `${appHint}_${promptHint}_${unique}${extension}`;
  const params = new URLSearchParams({
    filename: output.filename,
    subfolder: output.subfolder || "",
    type: output.type || "output",
    downloadName
  });
  return `/api/download?${params.toString()}`;
}

function ResultPreview({ outputs, jobId, values, appName }) {
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
  const downloadUrl = buildDownloadUrl(first, jobId, values, appName);

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
      <a className="download-button" href={`${API_BASE}${downloadUrl}`}>
        Download result
      </a>
      <p className="file-note">{first.filename}</p>
    </div>
  );
}

function loadSavedState() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveState(patch) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...loadSavedState(), ...patch, savedAt: Date.now() }));
  } catch {
    // Persistence is a convenience; the app still works if storage is unavailable.
  }
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
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    async function load() {
      const configResponse = await fetch(`${API_BASE}/api/config`);
      const nextConfig = await configResponse.json();
      setConfig(nextConfig);
      const defaults = Object.fromEntries((nextConfig.fields || []).map((field) => [field.name, defaultValue(field)]));
      const saved = loadSavedState();
      setValues({ ...defaults, ...(saved.values || {}) });
      if (saved.job?.jobId || saved.job?.promptId) {
        setJob(saved.job);
      }

      const statusResponse = await fetch(`${API_BASE}/api/status`);
      setStatus({ ...(await statusResponse.json()), checking: false });
    }
    load().catch((loadError) => {
      setStatus({ ok: false, checking: false, error: loadError.message });
    });
  }, []);

  useEffect(() => {
    if (!job?.jobId || ["complete", "error", "unknown"].includes(job.status)) return;
    const timer = setInterval(async () => {
      const response = await fetch(`${API_BASE}/api/jobs/${job.jobId}`);
      if (response.ok) {
        const nextJob = await response.json();
        setJob(nextJob);
        saveState({ job: nextJob });
        return;
      }
      if (job.promptId) {
        const recoveryResponse = await fetch(`${API_BASE}/api/prompts/${job.promptId}`);
        if (recoveryResponse.ok) {
          const recoveredJob = await recoveryResponse.json();
          setJob(recoveredJob);
          saveState({ job: recoveredJob });
        }
      }
    }, 1200);
    return () => clearInterval(timer);
  }, [job]);

  useEffect(() => {
    if (!job || restored) return;
    const shouldRecover = job.promptId && !["complete", "error", "unknown"].includes(job.status);
    if (!shouldRecover) return;
    setRestored(true);
    async function recover() {
      const response = await fetch(`${API_BASE}/api/jobs/${job.jobId}`);
      if (response.ok) {
        const nextJob = await response.json();
        setJob(nextJob);
        saveState({ job: nextJob });
        return;
      }
      const recoveryResponse = await fetch(`${API_BASE}/api/prompts/${job.promptId}`);
      if (recoveryResponse.ok) {
        const recoveredJob = await recoveryResponse.json();
        setJob(recoveredJob);
        saveState({ job: recoveredJob });
      }
    }
    recover().catch(() => {});
  }, [job, restored]);

  const busy = job && !["complete", "error"].includes(job.status);
  const progressPercent = Math.round((job?.progress || 0) * 100);

  const primaryFields = useMemo(() => (config?.fields || []).filter((field) => !field.advanced), [config]);
  const advancedFields = useMemo(() => (config?.fields || []).filter((field) => field.advanced), [config]);

  function updateValue(name, value) {
    setValues((current) => {
      const nextValues = { ...current, [name]: value };
      saveState({ values: nextValues });
      return nextValues;
    });
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
      const nextJob = { jobId: data.jobId, promptId: data.promptId, status: "queued", progress: 0.05, outputs: [] };
      setJob(nextJob);
      saveState({ values, job: nextJob });
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
          <ResultPreview outputs={job?.outputs} jobId={job?.jobId} values={values} appName={config?.appName} />
        </section>
      </section>
    </main>
  );
}
