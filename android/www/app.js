/* ScreenOCR móvil: captura (cámara/galería) + recorte + OCR (OCR.space) + trabajos locales. */
(() => {
  "use strict";

  const OCR_URL = "https://api.ocr.space/parse/image";
  const MAX_BYTES = 1_000_000;          // límite del plan gratuito de OCR.space
  const DEMO_KEY = "helloworld";
  const DONATIONS = [
    ["BITCOIN (BTC)", "bc1qd9j45f4t0jwyhjhqh2kvz2cr7k8xye460rr2y7"],
    ["MONERO (XMR)", "447gTj6Hg6gaAEAUmjqfhqDZr1PziUTvbT4LYLpmLVnTNVFK6cqeqPfh6P4neMKLWX5jDXAr94fWHacJwDvjmCzBBH8wPBt"],
    ["USDC (ARBITRUM)", "0xAC43f9b0E7F0ae6386cfC8ef6BFf62CE9c3006A1"],
  ];

  const $ = (id) => document.getElementById(id);
  const els = {
    menu: $("menuBtn"), sidebar: $("sidebar"), scrim: $("scrim"), list: $("jobList"), empty: $("emptyList"),
    preview: $("preview"), previewEmpty: $("previewEmpty"), editor: $("editor"), status: $("status"),
    retry: $("retryBtn"), copy: $("copyBtn"), save: $("saveBtn"),
    cameraBtn: $("cameraBtn"), galleryBtn: $("galleryBtn"),
    cameraInput: $("cameraInput"), galleryInput: $("galleryInput"),
    cropDlg: $("cropDlg"), cropBox: $("cropBox"), cropImg: $("cropImg"), cropSel: $("cropSel"),
    cropCancel: $("cropCancel"), cropAll: $("cropAll"), cropGo: $("cropGo"),
    renameDlg: $("renameDlg"), renameInput: $("renameInput"), renameCancel: $("renameCancel"), renameOk: $("renameOk"),
    confirmDlg: $("confirmDlg"), confirmText: $("confirmText"), confirmNo: $("confirmNo"), confirmYes: $("confirmYes"),
    donateDlg: $("donateDlg"), donateList: $("donateList"), donateBtn: $("donateBtn"), donateClose: $("donateClose"),
    settingsDlg: $("settingsDlg"), settingsBtn: $("settingsBtn"), apiKey: $("apiKeyInput"), lang: $("langInput"),
    engine: $("engineInput"), endpoint: $("endpointInput"), endpointField: $("endpointField"),
    apiField: $("apiKeyField"), engineHint: $("engineHint"),
    keyHint: $("keyHint"), settingsCancel: $("settingsCancel"), settingsSave: $("settingsSave"), toast: $("toast"),
  };

  // ---------- Configuración (por dispositivo) ----------
  const OCR_SPACE_URL = OCR_URL;
  const TESSERACT_CDN = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";
  const ENGINE_HINTS = {
    ocrspace: "OCR.space: API en la nube con clave gratuita. Requiere internet.",
    tesseract: "Tesseract.js: código abierto, corre en tu dispositivo, sin clave ni límites. Requiere internet solo la primera vez para cargar el motor y los idiomas.",
    custom: "Endpoint propio compatible con OCR.space (por ejemplo, un servidor que tú administras).",
  };
  const DEFAULT_CFG = { engine: "ocrspace", apiKey: DEMO_KEY, endpoint: OCR_SPACE_URL, language: "auto" };
  let cfg = { ...DEFAULT_CFG };
  try { cfg = { ...DEFAULT_CFG, ...JSON.parse(localStorage.getItem("screenocr.cfg") || "{}") }; } catch (_) {}
  function saveCfg() { try { localStorage.setItem("screenocr.cfg", JSON.stringify(cfg)); } catch (_) {} }

  // ---------- IndexedDB (trabajos + imagen JPEG) ----------
  const DB_NAME = "screenocr", STORE = "jobs";
  const dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "id" });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  async function dbRequest(mode, fn) {
    const db = await dbPromise;
    return new Promise((resolve, reject) => {
      const t = db.transaction(STORE, mode);
      const req = fn(t.objectStore(STORE));
      t.oncomplete = () => resolve(req ? req.result : undefined);
      t.onerror = () => reject(t.error);
    });
  }
  const dbAll = () => dbRequest("readonly", (s) => s.getAll());
  const dbGet = (id) => dbRequest("readonly", (s) => s.get(id));
  const dbPut = (job) => dbRequest("readwrite", (s) => s.put(job));
  const dbDel = (id) => dbRequest("readwrite", (s) => s.delete(id));

  // ---------- Estado ----------
  let jobs = [];
  let currentId = null;
  let previewUrl = null;
  let pendingBitmap = null;   // imagen elegida, a la espera de recorte
  let pendingSource = null;   // URL temporal del recorte
  let selection = null;       // {x,y,w,h} en px del elemento mostrado
  let dragStart = null;
  let confirmAction = null;

  // ---------- Utilidades ----------
  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.remove("show"), 2200);
  }
  function fmtDate(ts) {
    const d = new Date(ts);
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }
  const STATUS_TEXT = { pending: "Procesando…", done: "Listo", error: "Error" };
  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = () => reject(r.error);
      r.readAsDataURL(blob);
    });
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (_) {}
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  }

  // ---------- Imagen: recorte y compresión bajo 1 MB ----------
  async function encodeJpeg(bitmap, sx, sy, sw, sh) {
    let scale = Math.min(1, 2000 / Math.max(sw, sh));
    for (let i = 0; i < 6; i++) {
      const w = Math.max(1, Math.round(sw * scale));
      const h = Math.max(1, Math.round(sh * scale));
      const c = document.createElement("canvas");
      c.width = w; c.height = h;
      const ctx = c.getContext("2d");
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(bitmap, sx, sy, sw, sh, 0, 0, w, h);
      const blob = await new Promise((res) => c.toBlob(res, "image/jpeg", 0.9));
      if (blob && blob.size <= MAX_BYTES) return blob;
      scale *= 0.75;
    }
    throw new Error("La captura es demasiado grande para el plan gratuito (1 MB). Elige un área más pequeña.");
  }

  // ---------- OCR (OCR.space) ----------
  // Despacha al motor elegido en Configuración.
  async function runOcr(blob) {
    if (cfg.engine === "tesseract") return runTesseract(blob);
    if (cfg.engine === "custom") return runOcrSpace(blob, cfg.endpoint || OCR_SPACE_URL);
    return runOcrSpace(blob, OCR_SPACE_URL);
  }

  // Tesseract.js: se carga bajo demanda desde jsDelivr (código abierto, Apache-2.0).
  let tesseractLoading = null;
  function loadTesseract() {
    if (window.Tesseract) return Promise.resolve();
    if (!tesseractLoading) {
      tesseractLoading = new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = TESSERACT_CDN;
        s.onload = resolve;
        s.onerror = () => { tesseractLoading = null; reject(new Error("No se pudo cargar Tesseract.js. Revisa tu internet.")); };
        document.head.appendChild(s);
      });
    }
    return tesseractLoading;
  }
  async function runTesseract(blob) {
    await loadTesseract();
    // En 'auto' se leen inglés y español a la vez en la misma pasada.
    const langs = cfg.language === "eng" ? "eng" : cfg.language === "spa" ? "spa" : "eng+spa";
    const { data } = await window.Tesseract.recognize(blob, langs, { logger: () => {} });
    return (data.text || "").trim();
  }

  // Protocolo OCR.space (también usado por endpoints compatibles).
  async function runOcrSpace(blob, endpoint) {
    const body = new URLSearchParams({
      apikey: cfg.apiKey || DEMO_KEY,
      language: cfg.language,
      OCREngine: "2",
      scale: "true",
      detectOrientation: "true",
      isOverlayRequired: "false",
      base64Image: await blobToDataUrl(blob),
    });
    let resp;
    try {
      resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      });
    } catch (e) {
      throw new Error("Sin conexión con OCR.space. Revisa tu internet.");
    }
    if (resp.status === 401 || resp.status === 403) throw new Error("API key inválida o límite de uso alcanzado.");
    if (!resp.ok) throw new Error(`OCR.space respondió HTTP ${resp.status}.`);
    const payload = await resp.json();
    if (payload.IsErroredOnProcessing) {
      let err = payload.ErrorMessage || payload.ErrorDetails || "Error desconocido";
      if (Array.isArray(err)) err = err.join(" ");
      throw new Error(String(err));
    }
    return (payload.ParsedResults || []).map((r) => r.ParsedText || "").join("\n").trim();
  }

  async function processJob(id) {
    const job = await dbGet(id);
    if (!job) return;
    job.status = "pending";
    job.error = "";
    await dbPut(job);
    await refreshList();
    if (currentId === id) showJob(job);
    try {
      job.text = await runOcr(job.blob);
      job.status = "done";
    } catch (e) {
      job.status = "error";
      job.error = e.message || String(e);
    }
    await dbPut(job);
    await refreshList();
    if (currentId === id) showJob(job);
  }

  // ---------- Lista de trabajos ----------
  async function refreshList() {
    jobs = (await dbAll()).sort((a, b) => b.createdAt - a.createdAt);
    els.list.textContent = "";
    els.empty.hidden = jobs.length > 0;
    for (const job of jobs) {
      const li = document.createElement("li");
      li.dataset.id = job.id;
      if (job.id === currentId) li.classList.add("active");

      const meta = document.createElement("div");
      meta.className = "meta";
      const title = document.createElement("div");
      title.className = "title";
      title.textContent = job.title;
      const sub = document.createElement("div");
      sub.className = "sub";
      sub.textContent = `${STATUS_TEXT[job.status] || ""} · ${fmtDate(job.createdAt)}`;
      meta.append(title, sub);

      const edit = document.createElement("button");
      edit.className = "row-btn";
      edit.textContent = "✎";
      edit.setAttribute("aria-label", "Renombrar");
      edit.onclick = (ev) => { ev.stopPropagation(); openRename(job.id); };

      const del = document.createElement("button");
      del.className = "row-btn danger";
      del.textContent = "✕";
      del.setAttribute("aria-label", "Eliminar");
      del.onclick = (ev) => { ev.stopPropagation(); askDelete(job.id); };

      li.onclick = () => { selectJob(job.id); closeDrawer(); };
      li.append(meta, edit, del);
      els.list.appendChild(li);
    }
  }

  function setPreview(blob) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = blob ? URL.createObjectURL(blob) : null;
    els.preview.hidden = !previewUrl;
    els.previewEmpty.hidden = !!previewUrl;
    els.preview.src = previewUrl || "";
  }

  function setButtons(job) {
    const enabled = !!job;
    const busy = enabled && job.status === "pending";
    els.editor.disabled = !enabled;
    els.editor.readOnly = busy;
    els.save.disabled = !enabled || busy;
    els.copy.disabled = !enabled || busy;
    els.retry.disabled = !enabled || job.status !== "error";
  }

  function showJob(job) {
    currentId = job ? job.id : null;
    setPreview(job ? job.blob : null);
    els.editor.value = job ? (job.text || "") : "";
    setButtons(job);
    if (!job) { els.status.textContent = ""; return; }
    if (job.status === "pending") els.status.textContent = "Procesando OCR…";
    else if (job.status === "error") els.status.textContent = `Error: ${job.error}`;
    else if (!job.text.trim()) els.status.textContent = "No se detectó texto en la captura.";
    else els.status.textContent = "Listo";
    for (const li of els.list.children) li.classList.toggle("active", li.dataset.id === currentId);
  }

  async function selectJob(id) {
    const job = await dbGet(id);
    showJob(job || null);
  }

  // ---------- Acciones de trabajo ----------
  async function saveText() {
    const job = currentId && (await dbGet(currentId));
    if (!job || job.status === "pending") return;
    job.text = els.editor.value;
    await dbPut(job);
    await refreshList();
    els.status.textContent = "Guardado";
    toast("Guardado");
  }

  function openRename(id) {
    const job = jobs.find((j) => j.id === id);
    if (!job) return;
    els.renameInput.value = job.title;
    els.renameDlg.dataset.id = id;
    els.renameDlg.showModal();
    els.renameInput.focus();
  }
  async function confirmRename() {
    const name = els.renameInput.value.trim();
    const id = els.renameDlg.dataset.id;
    els.renameDlg.close();
    if (!name) return;
    const job = await dbGet(id);
    if (!job) return;
    job.title = name;
    await dbPut(job);
    await refreshList();
  }

  function askDelete(id) {
    const job = jobs.find((j) => j.id === id);
    if (!job) return;
    els.confirmText.textContent = `¿Eliminar «${job.title}» y su captura?`;
    confirmAction = async () => {
      await dbDel(id);
      if (currentId === id) showJob(null);
      await refreshList();
      toast("Trabajo eliminado");
    };
    els.confirmDlg.showModal();
  }

  // ---------- Captura y recorte ----------
  // Cámara: input con capture=environment abre la cámara trasera del celular.
  // Galería: selector normal de imágenes.
  function openPicker(input) { input.value = ""; input.click(); }

  async function onFilePicked(input) {
    const file = input.files && input.files[0];
    if (!file) return;
    try {
      pendingBitmap = await createImageBitmap(file);
    } catch (e) {
      toast("No se pudo abrir la imagen.");
      return;
    }
    if (pendingSource) URL.revokeObjectURL(pendingSource);
    pendingSource = URL.createObjectURL(file);
    els.cropImg.src = pendingSource;
    selection = null;
    els.cropSel.hidden = true;
    els.cropImg.onload = () => els.cropDlg.showModal();
  }

  function pointInImage(ev) {
    const r = els.cropImg.getBoundingClientRect();
    const x = Math.min(Math.max(ev.clientX - r.left, 0), r.width);
    const y = Math.min(Math.max(ev.clientY - r.top, 0), r.height);
    return { x, y };
  }
  function drawSelection(a, b) {
    const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
    const w = Math.abs(a.x - b.x), h = Math.abs(a.y - b.y);
    selection = { x, y, w, h };
    els.cropSel.hidden = false;
    Object.assign(els.cropSel.style, { left: x + "px", top: y + "px", width: w + "px", height: h + "px" });
  }
  els.cropBox.addEventListener("pointerdown", (ev) => {
    dragStart = pointInImage(ev);
    els.cropBox.setPointerCapture(ev.pointerId);
    drawSelection(dragStart, dragStart);
  });
  els.cropBox.addEventListener("pointermove", (ev) => {
    if (!dragStart) return;
    drawSelection(dragStart, pointInImage(ev));
  });
  els.cropBox.addEventListener("pointerup", () => {
    dragStart = null;
    if (selection && (selection.w < 8 || selection.h < 8)) { selection = null; els.cropSel.hidden = true; }
  });

  function closeCrop() {
    els.cropDlg.close();
    if (pendingSource) { URL.revokeObjectURL(pendingSource); pendingSource = null; }
    pendingBitmap = null;
    selection = null;
  }

  async function createJobFromBitmap(sx, sy, sw, sh) {
    const bitmap = pendingBitmap;
    if (!bitmap) return;
    let blob;
    try {
      blob = await encodeJpeg(bitmap, sx, sy, sw, sh);
    } catch (e) {
      toast(e.message);
      return;
    }
    const id = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
    const job = {
      id, title: `Captura ${fmtDate(Date.now())}`, createdAt: Date.now(),
      status: "pending", text: "", error: "", blob,
    };
    await dbPut(job);
    closeCrop();
    await refreshList();
    showJob(job);
    processJob(id);
  }

  function cropToSource() {
    const img = els.cropImg;
    const scaleX = img.naturalWidth / img.getBoundingClientRect().width;
    const scaleY = img.naturalHeight / img.getBoundingClientRect().height;
    return { scaleX, scaleY };
  }

  els.cropAll.onclick = () => {
    if (!pendingBitmap) return;
    createJobFromBitmap(0, 0, pendingBitmap.width, pendingBitmap.height);
  };
  els.cropGo.onclick = () => {
    if (!pendingBitmap) return;
    if (!selection) return els.cropAll.onclick();
    const { scaleX, scaleY } = cropToSource();
    createJobFromBitmap(
      Math.round(selection.x * scaleX), Math.round(selection.y * scaleY),
      Math.round(selection.w * scaleX), Math.round(selection.h * scaleY),
    );
  };
  els.cropCancel.onclick = closeCrop;
  els.cropDlg.addEventListener("cancel", closeCrop);

  // ---------- Botones principales ----------
  els.cameraBtn.onclick = () => openPicker(els.cameraInput);
  els.galleryBtn.onclick = () => openPicker(els.galleryInput);
  els.cameraInput.onchange = () => onFilePicked(els.cameraInput);
  els.galleryInput.onchange = () => onFilePicked(els.galleryInput);
  els.save.onclick = saveText;
  els.copy.onclick = async () => {
    const ok = await copyText(els.editor.value);
    els.status.textContent = ok ? "Texto copiado" : "No se pudo copiar";
  };
  els.retry.onclick = async () => {
    if (currentId) processJob(currentId);
  };
  els.renameOk.onclick = confirmRename;
  els.renameCancel.onclick = () => els.renameDlg.close();
  els.confirmYes.onclick = async () => {
    els.confirmDlg.close();
    if (confirmAction) await confirmAction();
    confirmAction = null;
  };
  els.confirmNo.onclick = () => { els.confirmDlg.close(); confirmAction = null; };

  // Cajón de trabajos (móvil)
  function openDrawer() { els.sidebar.classList.add("open"); els.scrim.classList.add("show"); }
  function closeDrawer() { els.sidebar.classList.remove("open"); els.scrim.classList.remove("show"); }
  els.menu.onclick = () => (els.sidebar.classList.contains("open") ? closeDrawer() : openDrawer());
  els.scrim.onclick = closeDrawer;

  // Donar
  els.donateBtn.onclick = () => {
    els.donateList.textContent = "";
    for (const [name, addr] of DONATIONS) {
      const wrap = document.createElement("div");
      wrap.className = "donate-item";
      const label = document.createElement("div");
      label.className = "donate-name";
      label.textContent = name;
      const row = document.createElement("div");
      row.className = "donate-row";
      const input = document.createElement("input");
      input.type = "text"; input.readOnly = true; input.value = addr;
      const btn = document.createElement("button");
      btn.textContent = "Copiar";
      btn.onclick = async () => {
        await copyText(addr);
        btn.textContent = "¡Copiado!";
        setTimeout(() => (btn.textContent = "Copiar"), 1500);
      };
      row.append(input, btn);
      wrap.append(label, row);
      els.donateList.appendChild(wrap);
    }
    els.donateDlg.showModal();
  };
  els.donateClose.onclick = () => els.donateDlg.close();

  // Configuración
  function refreshEngineFields() {
    const engine = els.engine.value;
    els.apiField.hidden = engine !== "ocrspace" && engine !== "custom";
    els.endpointField.hidden = engine !== "custom";
    els.engineHint.textContent = ENGINE_HINTS[engine];
    if (engine === "ocrspace") {
      els.keyHint.textContent = "Sin clave propia se usa la demo pública de OCR.space, con cuota compartida y limitada.";
    } else if (engine === "custom") {
      els.keyHint.textContent = "Si tu endpoint pide clave, escríbela aquí.";
    } else {
      els.keyHint.textContent = "";
    }
  }
  els.engine.onchange = refreshEngineFields;

  els.settingsBtn.onclick = () => {
    els.engine.value = cfg.engine;
    els.apiKey.value = cfg.apiKey === DEMO_KEY ? "" : cfg.apiKey;
    els.endpoint.value = cfg.endpoint || OCR_SPACE_URL;
    els.lang.value = cfg.language;
    refreshEngineFields();
    els.settingsDlg.showModal();
  };
  els.settingsCancel.onclick = () => els.settingsDlg.close();
  els.settingsSave.onclick = () => {
    cfg.engine = els.engine.value;
    cfg.apiKey = els.apiKey.value.trim() || DEMO_KEY;
    cfg.endpoint = els.endpoint.value.trim() || OCR_SPACE_URL;
    cfg.language = els.lang.value;
    saveCfg();
    els.settingsDlg.close();
    toast("Configuración guardada");
  };

  // Arranque
  refreshList().then(() => showJob(null));
})();
