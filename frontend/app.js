/* =============================================
   CONFIG
   ============================================= */
const API = '/api/v1';

/* =============================================
   STATE
   ============================================= */
const state = {
  page: 'dashboard',
  jobs: [],
  jobsTotal: 0,
  resumes: [],
  tailored: [],
  tailoredTotal: 0,
  selectedJobId: null,
  selectedResumeId: null,
  jobSearch: '',
};

/* =============================================
   API HELPERS
   ============================================= */
async function apiFetch(path, opts = {}) {
  try {
    const res = await fetch(API + path, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    if (res.status === 204) return null;
    return res.json();
  } catch (e) {
    throw e;
  }
}

const api = {
  stats: async () => {
    const [jobs, resumes, tailored] = await Promise.all([
      apiFetch('/jobs?limit=1'),
      apiFetch('/resumes?limit=1'),
      apiFetch('/tailor?limit=1'),
    ]);
    return { jobs: jobs.total, resumes: resumes.total, tailored: tailored.total };
  },
  getJobs: (offset = 0, limit = 50) => apiFetch(`/jobs?offset=${offset}&limit=${limit}`),
  scrapeJobs: (body) => apiFetch('/jobs/scrape', { method: 'POST', body: JSON.stringify(body) }),
  getResumes: () => apiFetch('/resumes'),
  uploadResume: (formData) => fetch(API + '/resumes', { method: 'POST', body: formData }).then(async r => {
    if (!r.ok) { const e = await r.json().catch(() => ({ detail: r.statusText })); throw new Error(e.detail); }
    return r.json();
  }),
  getTailored: (offset = 0, limit = 50) => apiFetch(`/tailor?offset=${offset}&limit=${limit}`),
  tailor: (job_id, resume_id) => apiFetch('/tailor', { method: 'POST', body: JSON.stringify({ job_id, resume_id }) }),
  getTailoredById: (id) => apiFetch(`/tailor/${id}`),
};

/* =============================================
   TOAST
   ============================================= */
function toast(msg, type = 'info') {
  const icons = { success: 'check-circle', error: 'alert-circle', info: 'info' };
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<i data-lucide="${icons[type]}"></i><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  lucide.createIcons({ nodes: [el] });
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity 0.3s'; setTimeout(() => el.remove(), 300); }, 3500);
}

/* =============================================
   MODAL
   ============================================= */
function openModal(title, bodyHtml) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-overlay').classList.remove('hidden');
  lucide.createIcons({ nodes: [document.getElementById('modal-overlay')] });
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

function handleModalOverlayClick(e) {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
}

/* =============================================
   ROUTER / NAVIGATION
   ============================================= */
function navigate(page) {
  state.page = page;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  renderPage();
}

/* =============================================
   RENDER DISPATCHER
   ============================================= */
function renderPage() {
  const content = document.getElementById('content');
  content.innerHTML = '<div class="skeleton-card"><div class="skeleton skeleton-line long"></div><div class="skeleton skeleton-line medium"></div></div>'.repeat(3);
  const pages = { dashboard: renderDashboard, jobs: renderJobs, resumes: renderResumes, tailor: renderTailor, history: renderHistory };
  (pages[state.page] || renderDashboard)();
}

function icons() {
  lucide.createIcons({ nodes: [document.getElementById('content'), document.getElementById('modal-overlay')] });
}

/* =============================================
   DASHBOARD
   ============================================= */
async function renderDashboard() {
  const content = document.getElementById('content');
  try {
    const [stats, jobsData, tailoredData] = await Promise.all([
      api.stats(),
      api.getJobs(0, 5),
      api.getTailored(0, 5),
    ]);
    state.jobs = jobsData.items;

    const recentJobsHtml = jobsData.items.length === 0
      ? `<div class="empty-state" style="padding:30px"><div class="empty-state-icon"><i data-lucide="briefcase"></i></div><p>No jobs fetched yet. Go to <strong>Job Finder</strong> to scrape.</p></div>`
      : jobsData.items.map(j => `
        <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)">
          <div style="flex:1;min-width:0">
            <div style="font-weight:500;font-size:.875rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(j.title)}</div>
            <div style="font-size:.78rem;color:var(--text-muted)">${esc(j.company || '—')} · ${esc(j.location || '—')}</div>
          </div>
          <span class="badge badge-${j.source}">${j.source}</span>
        </div>`).join('');

    const recentTailoredHtml = tailoredData.items.length === 0
      ? `<div class="empty-state" style="padding:30px"><div class="empty-state-icon"><i data-lucide="wand-2"></i></div><p>No tailored resumes yet.</p></div>`
      : tailoredData.items.map(t => `
        <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--border);cursor:pointer" onclick="viewTailored('${t.id}')">
          <div style="flex:1;min-width:0">
            <div style="font-size:.875rem;font-weight:500">Tailored Resume</div>
            <div style="font-size:.78rem;color:var(--text-muted)">${new Date(t.created_at).toLocaleDateString()} · ${t.tokens_used ? t.tokens_used + ' tokens' : '—'}</div>
          </div>
          <span class="badge badge-${t.status}">${t.status}</span>
        </div>`).join('');

    content.innerHTML = `
      <div class="page-header">
        <div class="page-header-text">
          <h1>Dashboard</h1>
          <p>Your job search automation overview</p>
        </div>
        <button class="btn btn-primary" onclick="navigate('jobs')">
          <i data-lucide="search"></i> Find Jobs
        </button>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon jobs"><i data-lucide="briefcase"></i></div>
          <div class="stat-info">
            <div class="stat-value">${stats.jobs}</div>
            <div class="stat-label">Jobs Fetched</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon resumes"><i data-lucide="file-text"></i></div>
          <div class="stat-info">
            <div class="stat-value">${stats.resumes}</div>
            <div class="stat-label">Resumes Uploaded</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon tailored"><i data-lucide="sparkles"></i></div>
          <div class="stat-info">
            <div class="stat-value">${stats.tailored}</div>
            <div class="stat-label">Tailored Resumes</div>
          </div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="card">
          <div class="card-title">Recent Jobs</div>
          ${recentJobsHtml}
          ${jobsData.total > 5 ? `<div style="padding-top:12px"><a onclick="navigate('jobs')" style="font-size:.8125rem;color:var(--accent);font-weight:500;cursor:pointer">View all ${jobsData.total} jobs →</a></div>` : ''}
        </div>
        <div class="card">
          <div class="card-title">Recent Tailored Resumes</div>
          ${recentTailoredHtml}
          ${tailoredData.total > 5 ? `<div style="padding-top:12px"><a onclick="navigate('history')" style="font-size:.8125rem;color:var(--accent);font-weight:500;cursor:pointer">View all ${tailoredData.total} →</a></div>` : ''}
        </div>
      </div>
    `;
    icons();
  } catch (e) {
    content.innerHTML = errorState(e.message);
    icons();
  }
}

/* =============================================
   JOBS PAGE
   ============================================= */
async function renderJobs() {
  const content = document.getElementById('content');
  try {
    const data = await api.getJobs(0, 100);
    state.jobs = data.items;
    state.jobsTotal = data.total;
    renderJobsUI();
  } catch (e) {
    content.innerHTML = errorState(e.message);
    icons();
  }
}

function renderJobsUI() {
  const content = document.getElementById('content');
  const filtered = state.jobs.filter(j => {
    const q = state.jobSearch.toLowerCase();
    return !q || j.title.toLowerCase().includes(q) || (j.company || '').toLowerCase().includes(q) || (j.location || '').toLowerCase().includes(q);
  });

  const jobsHtml = filtered.length === 0
    ? `<div class="empty-state">
        <div class="empty-state-icon"><i data-lucide="briefcase"></i></div>
        <h3>${state.jobs.length === 0 ? 'No jobs fetched yet' : 'No matching jobs'}</h3>
        <p>${state.jobs.length === 0 ? 'Use the scraper above to fetch jobs from LinkedIn, Naukri, and Indeed.' : 'Try a different search term.'}</p>
      </div>`
    : filtered.map(j => jobCardHtml(j)).join('');

  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-text">
        <h1>Job Finder</h1>
        <p>${state.jobsTotal} jobs in database</p>
      </div>
    </div>

    <!-- Scrape Panel -->
    <div class="scrape-panel">
      <h3><i data-lucide="search"></i> Scrape New Jobs</h3>
      <div class="form-row">
        <div class="form-group" style="margin:0">
          <label>Job Title / Keywords</label>
          <input type="text" id="scrape-query" placeholder="e.g. Python Developer, Data Scientist" />
        </div>
        <div class="form-group" style="margin:0">
          <label>Location</label>
          <input type="text" id="scrape-location" placeholder="e.g. Bangalore, Remote" />
        </div>
      </div>
      <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-top:14px">
        <div>
          <label style="margin-bottom:6px">Sources</label>
          <div class="checkbox-group">
            <label class="checkbox-label"><input type="checkbox" id="src-linkedin" checked> <span class="badge badge-linkedin">LinkedIn</span></label>
            <label class="checkbox-label"><input type="checkbox" id="src-naukri" checked> <span class="badge badge-naukri">Naukri</span></label>
            <label class="checkbox-label"><input type="checkbox" id="src-indeed" checked> <span class="badge badge-indeed">Indeed</span></label>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <div>
            <label>Pages per source</label>
            <select id="scrape-pages" style="width:80px;margin:0">
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3" selected>3</option>
              <option value="5">5</option>
            </select>
          </div>
          <button class="btn btn-primary btn-lg" id="btn-scrape" onclick="doScrape()">
            <i data-lucide="play"></i> Start Scraping
          </button>
        </div>
      </div>
    </div>

    <!-- Search + Jobs -->
    <div class="search-bar">
      <i data-lucide="search"></i>
      <input type="text" placeholder="Filter by title, company, location…" value="${esc(state.jobSearch)}" oninput="state.jobSearch=this.value;renderJobsUI()">
    </div>

    <div class="jobs-grid">${jobsHtml}</div>
  `;
  icons();
}

function jobCardHtml(j) {
  const ago = timeAgo(j.scraped_at);
  const desc = j.description ? j.description.slice(0, 160).replace(/\n/g, ' ') + (j.description.length > 160 ? '…' : '') : '';
  return `
    <div class="job-card">
      <div class="job-card-header">
        <div>
          <div class="job-card-title">${esc(j.title)}</div>
          <div class="job-card-company">${esc(j.company || '—')}</div>
        </div>
        <span class="badge badge-${j.source}">${j.source}</span>
      </div>
      <div class="job-card-meta">
        ${j.location ? `<span class="job-meta-item"><i data-lucide="map-pin"></i>${esc(j.location)}</span>` : ''}
        ${j.job_type ? `<span class="job-meta-item"><i data-lucide="clock"></i>${esc(j.job_type)}</span>` : ''}
        ${j.salary_range ? `<span class="job-meta-item"><i data-lucide="indian-rupee"></i>${esc(j.salary_range)}</span>` : ''}
        <span class="job-meta-item"><i data-lucide="calendar"></i>${ago}</span>
      </div>
      ${desc ? `<div class="job-desc-preview">${esc(desc)}</div>` : ''}
      <div class="job-card-actions">
        ${j.description ? `<button class="btn btn-secondary btn-sm" onclick="viewJobDesc('${j.id}')"><i data-lucide="eye"></i> View JD</button>` : ''}
        <button class="btn btn-primary btn-sm" onclick="goTailor('${j.id}')">
          <i data-lucide="wand-2"></i> Tailor Resume
        </button>
        ${j.source_url ? `<a href="${j.source_url}" target="_blank" class="btn btn-ghost btn-sm"><i data-lucide="external-link"></i></a>` : ''}
      </div>
    </div>`;
}

async function doScrape() {
  const query = document.getElementById('scrape-query').value.trim();
  if (!query) { toast('Please enter a job title or keywords', 'error'); return; }

  const sources = [];
  if (document.getElementById('src-linkedin').checked) sources.push('linkedin');
  if (document.getElementById('src-naukri').checked) sources.push('naukri');
  if (document.getElementById('src-indeed').checked) sources.push('indeed');
  if (sources.length === 0) { toast('Select at least one source', 'error'); return; }

  const btn = document.getElementById('btn-scrape');
  setLoading(btn, true, 'Scraping…');

  try {
    const result = await api.scrapeJobs({
      query,
      location: document.getElementById('scrape-location').value.trim(),
      sources,
      max_pages: parseInt(document.getElementById('scrape-pages').value),
    });
    toast(`Fetched ${result.fetched} jobs, saved ${result.upserted} new`, 'success');
    const data = await api.getJobs(0, 100);
    state.jobs = data.items;
    state.jobsTotal = data.total;
    renderJobsUI();
  } catch (e) {
    toast(e.message, 'error');
    setLoading(btn, false, null, 'Start Scraping', 'play');
  }
}

function viewJobDesc(id) {
  const job = state.jobs.find(j => j.id === id);
  if (!job) return;
  openModal(`${job.title} — ${job.company || ''}`, `
    <div style="margin-bottom:16px">
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
        <span class="badge badge-${job.source}">${job.source}</span>
        ${job.location ? `<span style="font-size:.8rem;color:var(--text-muted)"><b>Location:</b> ${esc(job.location)}</span>` : ''}
        ${job.salary_range ? `<span style="font-size:.8rem;color:var(--text-muted)"><b>Salary:</b> ${esc(job.salary_range)}</span>` : ''}
      </div>
    </div>
    <div style="white-space:pre-wrap;font-size:.8125rem;line-height:1.75;color:var(--text);background:#f8fafc;padding:16px;border-radius:8px;max-height:420px;overflow-y:auto">${esc(job.description || 'No description available.')}</div>
    <div style="margin-top:16px;display:flex;gap:8px">
      <button class="btn btn-primary" onclick="goTailor('${job.id}');closeModal()"><i data-lucide="wand-2"></i> Tailor My Resume</button>
      ${job.source_url ? `<a href="${job.source_url}" target="_blank" class="btn btn-secondary"><i data-lucide="external-link"></i> Open Original</a>` : ''}
    </div>
  `);
}

/* =============================================
   RESUMES PAGE
   ============================================= */
async function renderResumes() {
  const content = document.getElementById('content');
  try {
    const data = await api.getResumes();
    state.resumes = data.items;
    renderResumesUI();
  } catch (e) {
    content.innerHTML = errorState(e.message);
    icons();
  }
}

function renderResumesUI() {
  const content = document.getElementById('content');

  const listHtml = state.resumes.length === 0
    ? `<div class="empty-state">
        <div class="empty-state-icon"><i data-lucide="file-text"></i></div>
        <h3>No resumes yet</h3>
        <p>Upload your resume PDF above to get started.</p>
      </div>`
    : `<div class="resume-list">${state.resumes.map(resumeItemHtml).join('')}</div>`;

  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-text">
        <h1>My Resumes</h1>
        <p>${state.resumes.length} resume${state.resumes.length !== 1 ? 's' : ''} uploaded</p>
      </div>
    </div>

    <!-- Upload Card -->
    <div class="card" style="margin-bottom:20px">
      <div class="card-title">Upload New Resume</div>
      <div class="upload-zone" id="upload-zone" onclick="document.getElementById('resume-file').click()">
        <input type="file" id="resume-file" accept=".pdf" onchange="handleFileSelect(event)">
        <div class="upload-icon"><i data-lucide="upload-cloud"></i></div>
        <h3>Click to upload or drag & drop</h3>
        <p>PDF files only · Max 10 MB</p>
        <div id="selected-file" style="margin-top:10px;font-size:.8125rem;color:var(--accent);font-weight:500"></div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:14px">
        <div style="flex:1">
          <label>Label (optional)</label>
          <input type="text" id="resume-label" placeholder="e.g. Software Engineer - 2024" />
        </div>
        <div style="padding-top:20px">
          <button class="btn btn-primary" id="btn-upload" onclick="doUpload()">
            <i data-lucide="upload"></i> Upload Resume
          </button>
        </div>
      </div>
    </div>

    <!-- List -->
    ${listHtml}
  `;

  // Drag & drop
  const zone = document.getElementById('upload-zone');
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) { document.getElementById('resume-file').files = e.dataTransfer.files; handleFileSelect({ target: { files: [file] } }); }
  });

  icons();
}

function resumeItemHtml(r) {
  const size = r.file_size < 1024 * 1024 ? (r.file_size / 1024).toFixed(0) + ' KB' : (r.file_size / 1024 / 1024).toFixed(1) + ' MB';
  return `
    <div class="resume-item">
      <div class="resume-icon"><i data-lucide="file-text"></i></div>
      <div class="resume-info">
        <div class="resume-name">${esc(r.label || r.filename)}</div>
        <div class="resume-meta">${esc(r.filename)} · ${size} · ${new Date(r.created_at).toLocaleDateString()}</div>
      </div>
      <div class="resume-actions">
        ${r.parsed_text ? `<button class="btn btn-secondary btn-sm" onclick="viewResumeText('${r.id}')"><i data-lucide="eye"></i> Preview</button>` : ''}
        <a href="/api/v1/resumes/${r.id}/download" class="btn btn-ghost btn-sm" title="Download"><i data-lucide="download"></i></a>
        <button class="btn btn-primary btn-sm" onclick="goTailor(null,'${r.id}')"><i data-lucide="wand-2"></i> Tailor</button>
      </div>
    </div>`;
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) document.getElementById('selected-file').textContent = `Selected: ${file.name}`;
}

async function doUpload() {
  const fileInput = document.getElementById('resume-file');
  const file = fileInput.files[0];
  if (!file) { toast('Please select a PDF file', 'error'); return; }
  if (!file.name.endsWith('.pdf')) { toast('Only PDF files are accepted', 'error'); return; }

  const btn = document.getElementById('btn-upload');
  setLoading(btn, true, 'Uploading…');

  const formData = new FormData();
  formData.append('file', file);
  const label = document.getElementById('resume-label').value.trim();
  if (label) formData.append('label', label);

  try {
    const resume = await api.uploadResume(formData);
    const exists = state.resumes.find(r => r.id === resume.id);
    if (exists) {
      toast('This resume was already uploaded (duplicate detected)', 'info');
    } else {
      state.resumes.unshift(resume);
      toast('Resume uploaded and parsed successfully!', 'success');
    }
    renderResumesUI();
  } catch (e) {
    toast(e.message, 'error');
    setLoading(btn, false, null, 'Upload Resume', 'upload');
  }
}

function viewResumeText(id) {
  const r = state.resumes.find(x => x.id === id);
  if (!r) return;
  openModal(r.label || r.filename, `
    <div style="white-space:pre-wrap;font-size:.8125rem;line-height:1.75;color:var(--text);background:#f8fafc;padding:16px;border-radius:8px;max-height:480px;overflow-y:auto">${esc(r.parsed_text || 'No text extracted.')}</div>
    <div style="margin-top:14px;display:flex;gap:8px">
      <button class="btn btn-primary" onclick="goTailor(null,'${r.id}');closeModal()"><i data-lucide="wand-2"></i> Tailor to a Job</button>
    </div>
  `);
}

/* =============================================
   TAILOR PAGE
   ============================================= */
async function renderTailor() {
  const content = document.getElementById('content');
  try {
    const [jobsData, resumesData] = await Promise.all([api.getJobs(0, 100), api.getResumes()]);
    state.jobs = jobsData.items;
    state.resumes = resumesData.items;
    renderTailorUI();
  } catch (e) {
    content.innerHTML = errorState(e.message);
    icons();
  }
}

function renderTailorUI(result = null) {
  const content = document.getElementById('content');
  const jobListHtml = buildSelectorList(
    state.jobs,
    state.selectedJobId,
    j => `<div class="selector-item-title">${esc(j.title)}</div><div class="selector-item-sub">${esc(j.company || '—')} · <span class="badge badge-${j.source}" style="font-size:.68rem">${j.source}</span></div>`,
    id => selectJob(id),
    'jobs',
    'jobSearch'
  );

  const resumeListHtml = buildSelectorList(
    state.resumes,
    state.selectedResumeId,
    r => `<div class="selector-item-title">${esc(r.label || r.filename)}</div><div class="selector-item-sub">${esc(r.filename)} · ${new Date(r.created_at).toLocaleDateString()}</div>`,
    id => { state.selectedResumeId = id; renderTailorUI(); },
    'resumes',
    null
  );

  const selectedJob = state.jobs.find(j => j.id === state.selectedJobId);
  const selectedResume = state.resumes.find(r => r.id === state.selectedResumeId);
  const canTailor = state.selectedJobId && state.selectedResumeId;

  const resultHtml = result ? `
    <div class="tailor-result">
      <div class="tailor-result-header">
        <h3><i data-lucide="sparkles"></i> Tailored Resume Generated</h3>
        <div style="display:flex;gap:8px">
          <button class="btn btn-secondary btn-sm" onclick="copyText()"><i data-lucide="copy"></i> Copy</button>
          <button class="btn btn-secondary btn-sm" onclick="downloadText()"><i data-lucide="download"></i> Download</button>
        </div>
      </div>
      <div id="tailored-output" class="result-text">${esc(result.output_text || '')}</div>
      <div style="padding:12px 20px;border-top:1px solid var(--border);font-size:.78rem;color:var(--text-muted);display:flex;gap:16px">
        <span>Model: <b>${result.model_used}</b></span>
        ${result.tokens_used ? `<span>Tokens used: <b>${result.tokens_used.toLocaleString()}</b></span>` : ''}
        <span>Status: <span class="badge badge-${result.status}">${result.status}</span></span>
      </div>
    </div>` : '';

  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-text">
        <h1>AI Resume Tailor</h1>
        <p>Select a job and resume — AI will customize your resume to match the JD</p>
      </div>
    </div>

    <div class="tailor-layout">
      <!-- Job Selector -->
      <div class="selector-card">
        <div class="selector-header">
          <h3><i data-lucide="briefcase"></i> Select Job</h3>
          ${state.jobs.length === 0 ? `<button class="btn btn-secondary btn-sm" onclick="navigate('jobs')">Fetch Jobs</button>` : ''}
        </div>
        <div class="selector-search">
          <div class="search-bar" style="margin:0">
            <i data-lucide="search"></i>
            <input type="text" placeholder="Search jobs…" id="tailor-job-search" value="${esc(state.jobSearch)}" oninput="state.jobSearch=this.value;renderTailorUI()">
          </div>
        </div>
        <div class="selector-list">${jobListHtml}</div>
        ${selectedJob ? `<div class="selection-info"><i data-lucide="check-circle"></i> ${esc(selectedJob.title)} at ${esc(selectedJob.company || '—')}</div>` : ''}
      </div>

      <!-- Resume Selector -->
      <div class="selector-card">
        <div class="selector-header">
          <h3><i data-lucide="file-text"></i> Select Resume</h3>
          ${state.resumes.length === 0 ? `<button class="btn btn-secondary btn-sm" onclick="navigate('resumes')">Upload Resume</button>` : ''}
        </div>
        <div class="selector-list">${resumeListHtml}</div>
        ${selectedResume ? `<div class="selection-info"><i data-lucide="check-circle"></i> ${esc(selectedResume.label || selectedResume.filename)}</div>` : ''}
      </div>
    </div>

    <div class="tailor-action">
      <button class="btn btn-primary btn-lg" id="btn-tailor" onclick="doTailor()" ${canTailor ? '' : 'disabled'} style="${canTailor ? '' : 'opacity:.5;cursor:not-allowed'}">
        <i data-lucide="wand-2"></i> Generate Tailored Resume
      </button>
    </div>

    ${resultHtml}
  `;
  icons();
}

function buildSelectorList(items, selectedId, renderItem, onSelect, filterKey, searchKey) {
  const q = searchKey ? (state.jobSearch || '').toLowerCase() : '';
  const filtered = filterKey === 'jobs' && q
    ? items.filter(j => j.title.toLowerCase().includes(q) || (j.company || '').toLowerCase().includes(q))
    : items;

  if (filtered.length === 0) {
    return `<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:.875rem">
      ${items.length === 0 ? 'Nothing here yet' : 'No matches found'}
    </div>`;
  }

  return filtered.map(item => `
    <div class="selector-item ${item.id === selectedId ? 'selected' : ''}" onclick="${onSelect.toString().includes('selectJob') ? `selectJob('${item.id}')` : `(function(){state.selectedResumeId='${item.id}';renderTailorUI();})()`}">
      ${renderItem(item)}
    </div>`).join('');
}

function selectJob(id) {
  state.selectedJobId = id;
  renderTailorUI();
}

async function doTailor() {
  if (!state.selectedJobId || !state.selectedResumeId) return;
  const btn = document.getElementById('btn-tailor');
  setLoading(btn, true, 'AI is tailoring your resume…');

  try {
    const result = await api.tailor(state.selectedJobId, state.selectedResumeId);
    toast('Resume tailored successfully!', 'success');
    renderTailorUI(result);
  } catch (e) {
    toast(e.message, 'error');
    setLoading(btn, false, null, 'Generate Tailored Resume', 'wand-2');
  }
}

function copyText() {
  const text = document.getElementById('tailored-output')?.textContent;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => toast('Copied to clipboard!', 'success'));
}

function downloadText() {
  const text = document.getElementById('tailored-output')?.textContent;
  if (!text) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
  a.download = `tailored_resume_${Date.now()}.txt`;
  a.click();
  toast('Downloaded!', 'success');
}

/* =============================================
   HISTORY PAGE
   ============================================= */
async function renderHistory() {
  const content = document.getElementById('content');
  try {
    const [tailoredData, jobsData, resumesData] = await Promise.all([
      api.getTailored(0, 100),
      api.getJobs(0, 100),
      api.getResumes(),
    ]);
    state.tailored = tailoredData.items;
    state.jobs = jobsData.items;
    state.resumes = resumesData.items;

    const jobMap = Object.fromEntries(state.jobs.map(j => [j.id, j]));
    const resumeMap = Object.fromEntries(state.resumes.map(r => [r.id, r]));

    const rowsHtml = state.tailored.length === 0
      ? `<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-muted)">No tailored resumes yet. Go to <strong>AI Tailor</strong> to generate your first one.</td></tr>`
      : state.tailored.map(t => {
          const job = jobMap[t.job_id];
          const resume = resumeMap[t.resume_id];
          return `
            <tr>
              <td><div style="font-weight:500">${esc(job?.title || '—')}</div><div style="font-size:.75rem;color:var(--text-muted)">${esc(job?.company || '—')}</div></td>
              <td>${esc(resume?.label || resume?.filename || '—')}</td>
              <td><span class="badge badge-${t.status}">${t.status}</span></td>
              <td>${t.tokens_used ? t.tokens_used.toLocaleString() : '—'}</td>
              <td>${new Date(t.created_at).toLocaleDateString()}</td>
              <td>
                ${t.status === 'completed' ? `<button class="btn btn-secondary btn-sm" onclick="viewTailored('${t.id}')"><i data-lucide="eye"></i> View</button>` : ''}
              </td>
            </tr>`;
        }).join('');

    content.innerHTML = `
      <div class="page-header">
        <div class="page-header-text">
          <h1>Tailoring History</h1>
          <p>${tailoredData.total} tailored resume${tailoredData.total !== 1 ? 's' : ''} generated</p>
        </div>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Job</th>
              <th>Resume Used</th>
              <th>Status</th>
              <th>Tokens</th>
              <th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
    icons();
  } catch (e) {
    content.innerHTML = errorState(e.message);
    icons();
  }
}

async function viewTailored(id) {
  try {
    const t = await api.getTailoredById(id);
    openModal('Tailored Resume', `
      <div style="margin-bottom:14px;display:flex;gap:8px;flex-wrap:wrap">
        <span class="badge badge-${t.status}">${t.status}</span>
        <span style="font-size:.8rem;color:var(--text-muted)">Model: ${t.model_used}</span>
        ${t.tokens_used ? `<span style="font-size:.8rem;color:var(--text-muted)">${t.tokens_used.toLocaleString()} tokens</span>` : ''}
      </div>
      <div style="white-space:pre-wrap;font-size:.8125rem;line-height:1.75;color:var(--text);background:#f8fafc;padding:16px;border-radius:8px;max-height:440px;overflow-y:auto">${esc(t.output_text || t.error_msg || 'No output.')}</div>
      <div style="margin-top:14px;display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" onclick="navigator.clipboard.writeText(document.querySelector('.modal-body pre, .modal-body div[style*=pre-wrap]')?.textContent||'').then(()=>toast('Copied!','success'))"><i data-lucide="copy"></i> Copy</button>
      </div>
    `);
  } catch (e) {
    toast(e.message, 'error');
  }
}

/* =============================================
   HELPERS
   ============================================= */
function goTailor(jobId = null, resumeId = null) {
  if (jobId) state.selectedJobId = jobId;
  if (resumeId) state.selectedResumeId = resumeId;
  navigate('tailor');
}

function setLoading(btn, loading, loadingText, originalText, originalIcon) {
  if (loading) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> ${loadingText}`;
  } else {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="${originalIcon}"></i> ${originalText}`;
    lucide.createIcons({ nodes: [btn] });
  }
}

function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function errorState(msg) {
  return `<div class="empty-state">
    <div class="empty-state-icon"><i data-lucide="alert-circle"></i></div>
    <h3>Something went wrong</h3>
    <p>${esc(msg)}</p>
    <button class="btn btn-primary" style="margin-top:16px" onclick="renderPage()"><i data-lucide="refresh-cw"></i> Retry</button>
  </div>`;
}

/* =============================================
   INIT
   ============================================= */
document.addEventListener('click', e => {
  const navItem = e.target.closest('.nav-item');
  if (navItem && navItem.dataset.page) {
    e.preventDefault();
    navigate(navItem.dataset.page);
  }
});

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  renderPage();
});
