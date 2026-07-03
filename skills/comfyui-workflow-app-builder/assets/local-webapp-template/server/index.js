import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");
const distDir = path.join(rootDir, "dist");
const app = express();

const APP_HOST = process.env.APP_HOST || "0.0.0.0";
const APP_PORT = Number(process.env.APP_PORT || 17000);
const COMFY_URL = (process.env.COMFY_URL || "http://127.0.0.1:8188").replace(/\/$/, "");
const WORKFLOW_PATH = process.env.WORKFLOW_PATH || path.join(rootDir, "workflows", "workflow_api.json");
const MAP_PATH = process.env.WORKFLOW_MAP_PATH || path.join(rootDir, "config", "workflow-map.json");
const TIMEOUT_SECONDS = Number(process.env.GENERATION_TIMEOUT_SECONDS || 900);

const jobs = new Map();

app.use(express.json({ limit: "2mb" }));
if (fs.existsSync(distDir)) {
  app.use(express.static(distDir));
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function patchWorkflow(values) {
  const workflow = structuredClone(readJson(WORKFLOW_PATH));
  const map = readJson(MAP_PATH);

  for (const field of map.fields || []) {
    if (!(field.name in values)) continue;
    const node = workflow[field.node_id];
    if (!node) throw new Error(`Workflow node ${field.node_id} for ${field.name} was not found.`);
    if (!node.inputs || !(field.input in node.inputs)) {
      throw new Error(`Input ${field.input} was not found on node ${field.node_id}.`);
    }
    node.inputs[field.input] = coerceValue(values[field.name], field);
  }

  return workflow;
}

function coerceValue(value, field) {
  if (field.required && (value === undefined || value === null || String(value).trim() === "")) {
    throw new Error(`${field.label || field.name} is required.`);
  }

  if (field.type === "select") {
    const text = String(value ?? "");
    const options = field.options || [];
    if (options.length && !options.includes(text)) {
      throw new Error(`${field.label || field.name} must be one of: ${options.join(", ")}.`);
    }
    return text;
  }

  if (field.type === "number" || field.type === "slider") {
    const number = Number(value);
    if (!Number.isFinite(number)) throw new Error(`${field.label || field.name} must be a number.`);
    if (field.min !== undefined && number < Number(field.min)) {
      throw new Error(`${field.label || field.name} must be at least ${field.min}.`);
    }
    if (field.max !== undefined && number > Number(field.max)) {
      throw new Error(`${field.label || field.name} must be at most ${field.max}.`);
    }
    if (field.valueType === "int") return Math.round(number);
    return number;
  }

  if (field.type === "toggle") return Boolean(value);

  const text = String(value ?? "");
  if (field.maxLength && text.length > Number(field.maxLength)) {
    throw new Error(`${field.label || field.name} is too long.`);
  }
  return text;
}

async function comfyFetch(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`ComfyUI ${response.status}: ${text || response.statusText}`);
  }
  return response;
}

function collectOutputs(historyItem) {
  const outputs = [];
  const outputNodes = historyItem?.outputs || {};
  for (const nodeOutput of Object.values(outputNodes)) {
    for (const key of ["videos", "gifs", "images", "audio", "files"]) {
      for (const item of nodeOutput?.[key] || []) {
        const query = new URLSearchParams({
          filename: item.filename,
          subfolder: item.subfolder || "",
          type: item.type || "output"
        });
        outputs.push({
          kind: key,
          filename: item.filename,
          subfolder: item.subfolder || "",
          type: item.type || "output",
          url: `/api/view?${query.toString()}`
        });
      }
    }
  }
  return outputs;
}

function sanitizeDownloadName(value) {
  return String(value || "comfyui-output")
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "-")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 160) || "comfyui-output";
}

async function pollJob(jobId) {
  const job = jobs.get(jobId);
  const start = Date.now();

  while (Date.now() - start < TIMEOUT_SECONDS * 1000) {
    try {
      const response = await comfyFetch(`${COMFY_URL}/history/${job.promptId}`);
      const history = await response.json();
      if (history[job.promptId]) {
        job.status = "complete";
        job.progress = 1;
        job.outputs = collectOutputs(history[job.promptId]);
        jobs.set(jobId, job);
        return;
      }
      job.status = "running";
      job.progress = Math.min(0.95, job.progress + 0.03);
      jobs.set(jobId, job);
    } catch (error) {
      job.status = "error";
      job.error = error.message;
      jobs.set(jobId, job);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }

  job.status = "error";
  job.error = "Generation timed out.";
  jobs.set(jobId, job);
}

async function recoverPrompt(promptId) {
  const historyResponse = await comfyFetch(`${COMFY_URL}/history/${promptId}`);
  const history = await historyResponse.json();
  if (history[promptId]) {
    return {
      jobId: `recovered-${promptId}`,
      promptId,
      status: "complete",
      progress: 1,
      outputs: collectOutputs(history[promptId]),
      error: null
    };
  }

  const queueResponse = await comfyFetch(`${COMFY_URL}/queue`);
  const queue = await queueResponse.json();
  const running = Array.isArray(queue.queue_running) && queue.queue_running.some((item) => JSON.stringify(item).includes(promptId));
  const pending = Array.isArray(queue.queue_pending) && queue.queue_pending.some((item) => JSON.stringify(item).includes(promptId));

  if (running || pending) {
    return {
      jobId: `recovered-${promptId}`,
      promptId,
      status: running ? "running" : "queued",
      progress: running ? 0.5 : 0.1,
      outputs: [],
      error: null
    };
  }

  return {
    jobId: `recovered-${promptId}`,
    promptId,
    status: "unknown",
    progress: 0,
    outputs: [],
    error: "This prompt is no longer in ComfyUI history or queue."
  };
}

app.get("/api/config", (_request, response) => {
  const map = readJson(MAP_PATH);
  response.json({
    appName: map.appName || "ComfyUI Workflow App",
    outputType: map.outputType || "auto",
    fields: map.fields || []
  });
});

app.get("/api/status", async (_request, response) => {
  try {
    await comfyFetch(`${COMFY_URL}/object_info`);
    response.json({ ok: true, comfyUrl: COMFY_URL });
  } catch (error) {
    response.status(503).json({ ok: false, comfyUrl: COMFY_URL, error: error.message });
  }
});

app.post("/api/generate", async (request, response) => {
  try {
    const workflow = patchWorkflow(request.body || {});
    const clientId = crypto.randomUUID();
    const comfyResponse = await comfyFetch(`${COMFY_URL}/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: workflow, client_id: clientId })
    });
    const data = await comfyResponse.json();
    if (!data.prompt_id) throw new Error("ComfyUI did not return a prompt_id.");

    const jobId = crypto.randomUUID();
    jobs.set(jobId, {
      jobId,
      promptId: data.prompt_id,
      clientId,
      status: "queued",
      progress: 0.05,
      outputs: [],
      error: null
    });
    pollJob(jobId);
    response.json({ jobId, promptId: data.prompt_id, clientId });
  } catch (error) {
    response.status(400).json({ error: error.message });
  }
});

app.get("/api/jobs/:jobId", (request, response) => {
  const job = jobs.get(request.params.jobId);
  if (!job) return response.status(404).json({ error: "Job not found." });
  response.json(job);
});

app.get("/api/prompts/:promptId", async (request, response) => {
  try {
    response.json(await recoverPrompt(request.params.promptId));
  } catch (error) {
    response.status(404).json({ error: error.message });
  }
});

app.get("/api/view", async (request, response) => {
  try {
    const query = new URLSearchParams({
      filename: String(request.query.filename || ""),
      subfolder: String(request.query.subfolder || ""),
      type: String(request.query.type || "output")
    });
    const comfyResponse = await comfyFetch(`${COMFY_URL}/view?${query.toString()}`);
    response.setHeader("content-type", comfyResponse.headers.get("content-type") || "application/octet-stream");
    const buffer = Buffer.from(await comfyResponse.arrayBuffer());
    response.send(buffer);
  } catch (error) {
    response.status(404).json({ error: error.message });
  }
});

app.get("/api/download", async (request, response) => {
  try {
    const query = new URLSearchParams({
      filename: String(request.query.filename || ""),
      subfolder: String(request.query.subfolder || ""),
      type: String(request.query.type || "output")
    });
    const comfyResponse = await comfyFetch(`${COMFY_URL}/view?${query.toString()}`);
    const requestedName = sanitizeDownloadName(request.query.downloadName || request.query.filename);
    response.setHeader("content-type", comfyResponse.headers.get("content-type") || "application/octet-stream");
    response.setHeader("content-disposition", `attachment; filename="${requestedName}"`);
    const buffer = Buffer.from(await comfyResponse.arrayBuffer());
    response.send(buffer);
  } catch (error) {
    response.status(404).json({ error: error.message });
  }
});

app.get("*", (request, response, next) => {
  if (request.path.startsWith("/api/")) return next();
  const indexPath = path.join(distDir, "index.html");
  if (fs.existsSync(indexPath)) return response.sendFile(indexPath);
  response.status(404).send("Frontend build not found. Run npm run build, then start the server.");
});

app.listen(APP_PORT, APP_HOST, () => {
  const sameMachineUrl = `http://127.0.0.1:${APP_PORT}`;
  console.log(`ComfyUI workflow app listening on http://${APP_HOST}:${APP_PORT}`);
  console.log(`Open on this machine: ${sameMachineUrl}`);
  console.log(`ComfyUI backend: ${COMFY_URL}`);
  console.log(`Workflow: ${WORKFLOW_PATH}`);
});
