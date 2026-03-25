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
  jobPlatformFilter: [],
  jobAppliedFilter: '',
  notAppliedPage: 1,
  appliedPage: 1,
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
  applyTailor: (id, decisions, fullTextOverride) => apiFetch(`/tailor/${id}/apply`, { method: 'POST', body: JSON.stringify({ accepted_sections: decisions.map(d => d.section), edited_changes: decisions, full_text_override: fullTextOverride || null }) }),
  getTailoredById: (id) => apiFetch(`/tailor/${id}`),
  tailoredPdfUrl: (id) => `${API}/tailor/${id}/download`,
  tailoredDocxUrl: (id) => `${API}/tailor/${id}/download/docx`,
  resumePdfUrl: (id) => `${API}/resumes/${id}/download`,
  deleteResume: (id) => apiFetch(`/resumes/${id}`, { method: 'DELETE' }),
  getTailoredByJob: (job_id) => apiFetch(`/tailor?job_id=${job_id}&limit=20`),
  deleteTailored: (id) => apiFetch(`/tailor/${id}`, { method: 'DELETE' }),
  deleteJob: (id) => apiFetch(`/jobs/${id}`, { method: 'DELETE' }),
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
  const pages = { dashboard: renderDashboard, jobs: renderJobs, resumes: renderResumes, history: renderHistory };
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
    const data = await api.getJobs(0, 200);
    state.jobs = data.items;
    state.jobsTotal = data.total;
    state.notAppliedPage = 1;
    state.appliedPage = 1;
    renderJobsUI();
  } catch (e) {
    content.innerHTML = errorState(e.message);
    icons();
  }
}

function renderJobsUI() {
  const content = document.getElementById('content');
  const platform = state.jobPlatformFilter[0] || '';
  const PAGE_SIZE = 10;

  const filtered = state.jobs.filter(j => {
    const q = state.jobSearch.toLowerCase();
    const matchesSearch  = !q || j.title.toLowerCase().includes(q) || (j.company || '').toLowerCase().includes(q) || (j.location || '').toLowerCase().includes(q);
    const matchesPlatform = !platform || j.source === platform;
    return matchesSearch && matchesPlatform;
  });

  const notApplied = filtered.filter(j => !j.applied);
  const applied    = filtered.filter(j => j.applied);

  // Clamp pages
  const naTotalPages = Math.max(1, Math.ceil(notApplied.length / PAGE_SIZE));
  const aTotalPages  = Math.max(1, Math.ceil(applied.length / PAGE_SIZE));
  state.notAppliedPage = Math.min(state.notAppliedPage, naTotalPages);
  state.appliedPage    = Math.min(state.appliedPage, aTotalPages);

  const naSlice = notApplied.slice((state.notAppliedPage - 1) * PAGE_SIZE, state.notAppliedPage * PAGE_SIZE);
  const aSlice  = applied.slice((state.appliedPage - 1) * PAGE_SIZE, state.appliedPage * PAGE_SIZE);

  function paginationHtml(cur, total, prevExpr, nextExpr) {
    if (total <= 1) return '';
    return `<div class="pagination">
      <button class="btn btn-secondary btn-sm" ${cur === 1 ? 'disabled' : ''} onclick="${prevExpr}"><i data-lucide="chevron-left"></i> Prev</button>
      <span class="page-info">Page ${cur} of ${total}</span>
      <button class="btn btn-secondary btn-sm" ${cur === total ? 'disabled' : ''} onclick="${nextExpr}">Next <i data-lucide="chevron-right"></i></button>
    </div>`;
  }

  const notAppliedHtml = notApplied.length === 0
    ? `<div class="empty-state" style="padding:24px 0"><div class="empty-state-icon"><i data-lucide="briefcase"></i></div>
        <p>${state.jobs.length === 0 ? 'Use the scraper above to fetch jobs.' : 'No matching jobs.'}</p></div>`
    : `<div class="jobs-grid">${naSlice.map(j => jobCardHtml(j)).join('')}</div>
       ${paginationHtml(state.notAppliedPage, naTotalPages, 'state.notAppliedPage--;renderJobsUI()', 'state.notAppliedPage++;renderJobsUI()')}`;

  const appliedHtml = applied.length === 0
    ? `<div class="empty-state" style="padding:24px 0"><div class="empty-state-icon"><i data-lucide="check-circle"></i></div>
        <p>No applied jobs yet. Click <strong>Mark Applied</strong> on any job card above.</p></div>`
    : `<div class="jobs-grid">${aSlice.map(j => jobCardHtml(j)).join('')}</div>
       ${paginationHtml(state.appliedPage, aTotalPages, 'state.appliedPage--;renderJobsUI()', 'state.appliedPage++;renderJobsUI()')}`;

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

    <!-- Search + Filter -->
    <div class="search-bar">
      <i data-lucide="search"></i>
      <input type="text" placeholder="Filter by title, company, location…" value="${esc(state.jobSearch)}" oninput="state.jobSearch=this.value;state.notAppliedPage=1;state.appliedPage=1;renderJobsUI()">
    </div>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;flex-wrap:wrap">
      <div style="display:flex;align-items:center;gap:6px">
        <label style="font-size:.8125rem;color:var(--text-muted);font-weight:500;white-space:nowrap">Platform</label>
        <select style="margin:0;min-width:120px" onchange="state.jobPlatformFilter=this.value?[this.value]:[];state.notAppliedPage=1;state.appliedPage=1;renderJobsUI()">
          <option value="" ${!platform?'selected':''}>All Platforms</option>
          <option value="linkedin" ${platform==='linkedin'?'selected':''}>LinkedIn</option>
          <option value="naukri"   ${platform==='naukri'  ?'selected':''}>Naukri</option>
          <option value="indeed"   ${platform==='indeed'  ?'selected':''}>Indeed</option>
        </select>
      </div>
      <span style="margin-left:auto;font-size:.8125rem;color:var(--text-muted)">${filtered.length} of ${state.jobs.length} jobs</span>
    </div>

    <!-- Not Applied Section -->
    <div class="jobs-section">
      <div class="jobs-section-header">
        <i data-lucide="briefcase"></i>
        <h2>Not Applied</h2>
        <span class="section-count">${notApplied.length}</span>
      </div>
      ${notAppliedHtml}
    </div>

    <!-- Applied Section -->
    <div class="jobs-section" style="margin-top:32px">
      <div class="jobs-section-header applied">
        <i data-lucide="check-circle"></i>
        <h2>Applied</h2>
        <span class="section-count applied">${applied.length}</span>
      </div>
      ${appliedHtml}
    </div>
  `;
  icons();
}

function jobCardHtml(j) {
  const ago = j.posted_at ? formatJobDate(j.posted_at) : null;
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
        ${ago ? `<span class="job-meta-item"><i data-lucide="calendar"></i>${ago}</span>` : ''}
      </div>
      ${desc ? `<div class="job-desc-preview">${esc(desc)}</div>` : ''}
      <div class="job-card-actions">
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          ${j.description ? `<button class="btn btn-secondary btn-sm" onclick="viewJobDesc('${j.id}')"><i data-lucide="eye"></i> View JD</button>` : ''}
          <button class="btn btn-primary btn-sm" onclick="goTailor('${j.id}')">
            <i data-lucide="wand-2"></i> Tailor Resume
          </button>
          <button class="btn btn-sm ${j.applied ? 'btn-applied-active' : 'btn-applied'}" onclick="toggleApplied('${j.id}')">
            <i data-lucide="${j.applied ? 'check-circle' : 'circle'}"></i> ${j.applied ? 'Applied' : 'Mark Applied'}
          </button>
          ${j.source_url ? `<a href="${j.source_url}" target="_blank" class="btn btn-ghost btn-sm"><i data-lucide="external-link"></i></a>` : ''}
        </div>
        <button class="btn btn-danger btn-sm" onclick="deleteJob('${j.id}','${esc(j.title)}')" title="Delete job"><i data-lucide="trash-2"></i></button>
      </div>
      <div id="tailored-section-${j.id}" class="job-tailored-section">
        <button class="job-tailored-toggle" onclick="toggleJobTailored('${j.id}', this)">
          <i data-lucide="chevron-down"></i> Show Tailored Resumes
        </button>
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
    const data = await api.getJobs(0, 200);
    state.jobs = data.items;
    state.jobsTotal = data.total;
    state.notAppliedPage = 1;
    state.appliedPage = 1;
    renderJobsUI();
  } catch (e) {
    toast(e.message, 'error');
    setLoading(btn, false, null, 'Start Scraping', 'play');
  }
}

async function deleteJob(id, title) {
  if (!confirm(`Delete "${title}"?\nThis cannot be undone.`)) return;
  try {
    await api.deleteJob(id);
    state.jobs = state.jobs.filter(j => j.id !== id);
    state.jobsTotal = Math.max(0, state.jobsTotal - 1);
    toast('Job deleted', 'success');
    renderJobsUI();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function toggleApplied(id) {
  const job = state.jobs.find(j => j.id === id);
  if (!job) return;
  const newApplied = !job.applied;
  try {
    await apiFetch(`/jobs/${id}/applied`, { method: 'PATCH', body: JSON.stringify({ applied: newApplied }) });
    job.applied = newApplied;
    renderJobsUI();
    toast(newApplied ? 'Marked as applied ✓' : 'Moved back to Not Applied', 'success');
  } catch (e) {
    toast(e.message, 'error');
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

async function toggleJobTailored(jobId, btn) {
  const section = document.getElementById(`tailored-section-${jobId}`);
  const isOpen = section.dataset.open === '1';

  if (isOpen) {
    section.dataset.open = '0';
    btn.innerHTML = '<i data-lucide="chevron-down"></i> Show Tailored Resumes';
    const list = section.querySelector('.tailored-list');
    if (list) list.remove();
    lucide.createIcons({ nodes: [btn] });
    return;
  }

  btn.innerHTML = '<span class="spinner" style="width:12px;height:12px;border-width:2px"></span> Loading…';
  try {
    const data = await api.getTailoredByJob(jobId);
    section.dataset.open = '1';
    btn.innerHTML = '<i data-lucide="chevron-up"></i> Hide Tailored Resumes';
    lucide.createIcons({ nodes: [btn] });

    const items = (data.items || []).filter(t => t.status === 'completed');
    const listHtml = items.length === 0
      ? `<div style="font-size:.8rem;color:var(--text-muted);padding:8px 0">No tailored resumes yet for this job.</div>`
      : items.map((t, idx) => {
          const isDocxOut = t.output_path && t.output_path.endsWith('.docx');
          const dlUrl  = api.tailoredPdfUrl(t.id);  // endpoint auto-detects format
          const docxUrl = api.tailoredDocxUrl(t.id);
          return `
          <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 10px;background:var(--bg);border-radius:6px;margin-bottom:6px;flex-wrap:wrap;gap:6px">
            <span style="font-size:.8rem;color:var(--text);font-weight:500">
              <i data-lucide="file" style="width:13px;height:13px;vertical-align:middle;margin-right:4px"></i>
              Tailored Resume #${idx + 1}
              <span style="font-size:.72rem;color:var(--text-muted);margin-left:6px">${new Date(t.created_at).toLocaleDateString('en-IN', {day:'2-digit',month:'short',year:'numeric'})}</span>
            </span>
            <div style="display:flex;gap:6px">
              ${isDocxOut
                ? `<a href="${dlUrl}" download="tailored_resume.docx" class="btn btn-primary btn-sm"><i data-lucide="download"></i> Download DOCX</a>`
                : `<a href="${dlUrl}" target="_blank" class="btn btn-secondary btn-sm"><i data-lucide="eye"></i> View PDF</a>
                   <a href="${dlUrl}" download="tailored_resume.pdf" class="btn btn-secondary btn-sm"><i data-lucide="file-text"></i> PDF</a>
                   <a href="${docxUrl}" download="tailored_resume.docx" class="btn btn-secondary btn-sm"><i data-lucide="file"></i> DOC</a>`
              }
              <button class="btn btn-danger btn-sm" onclick="doDeleteTailored('${t.id}','${jobId}',this)"><i data-lucide="trash-2"></i></button>
            </div>
          </div>`;
        }).join('');

    const div = document.createElement('div');
    div.className = 'tailored-list';
    div.style.marginTop = '10px';
    div.innerHTML = listHtml;
    section.appendChild(div);
    lucide.createIcons({ nodes: [div] });
  } catch (e) {
    btn.innerHTML = '<i data-lucide="chevron-down"></i> Show Tailored Resumes';
    lucide.createIcons({ nodes: [btn] });
    toast('Failed to load tailored resumes', 'error');
  }
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
        <input type="file" id="resume-file" accept=".docx" onchange="handleFileSelect(event)">
        <div class="upload-icon"><i data-lucide="upload-cloud"></i></div>
        <h3>Click to upload or drag & drop</h3>
        <p>DOCX files only · Max 10 MB</p>
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
  const isDocx = r.filename.toLowerCase().endsWith('.docx');
  const viewBtn = isDocx
    ? `<a href="/api/v1/resumes/${r.id}/download" download="${esc(r.filename)}" class="btn btn-secondary btn-sm"><i data-lucide="download"></i> Download</a>`
    : `<button class="btn btn-secondary btn-sm" onclick="viewResumeText('${r.id}')"><i data-lucide="file-text"></i> View PDF</button>`;
  return `
    <div class="resume-item">
      <div class="resume-icon"><i data-lucide="${isDocx ? 'file' : 'file-text'}"></i></div>
      <div class="resume-info">
        <div class="resume-name">${esc(r.label || r.filename)}</div>
        <div class="resume-meta">${esc(r.filename)} · ${size} · ${new Date(r.created_at).toLocaleDateString()}</div>
      </div>
      <div class="resume-actions">
        ${viewBtn}
        <button class="btn btn-primary btn-sm" onclick="goTailor(null,'${r.id}')"><i data-lucide="wand-2"></i> Tailor</button>
        <button class="btn btn-danger btn-sm" onclick="doDeleteResume('${r.id}','${esc(r.label||r.filename)}')"><i data-lucide="trash-2"></i> Delete</button>
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
  if (!file) { toast('Please select a DOCX file', 'error'); return; }
  if (!file.name.match(/\.docx$/i)) { toast('Only DOCX files are accepted', 'error'); return; }

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

async function doDeleteTailored(id, jobId, btn) {
  if (!confirm('Delete this tailored resume? This cannot be undone.')) return;
  try {
    await api.deleteTailored(id);
    toast('Tailored resume deleted', 'success');
    // Re-render the tailored list for this job
    const section = document.getElementById(`tailored-section-${jobId}`);
    if (section) {
      const list = section.querySelector('.tailored-list');
      if (list) list.remove();
      section.dataset.open = '0';
      const toggleBtn = section.previousElementSibling;
      if (toggleBtn) {
        toggleBtn.innerHTML = '<i data-lucide="chevron-down"></i> Show Tailored Resumes';
        lucide.createIcons({ nodes: [toggleBtn] });
        toggleJobTailored(jobId, toggleBtn);
      }
    }
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function doDeleteResume(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  try {
    await api.deleteResume(id);
    state.resumes = state.resumes.filter(r => r.id !== id);
    toast('Resume deleted', 'success');
    renderResumesUI();
  } catch (e) {
    toast(e.message, 'error');
  }
}

function viewResumeText(id) {
  const r = state.resumes.find(x => x.id === id);
  if (!r) return;
  const pdfUrl = api.resumePdfUrl(id);
  openModal(r.label || r.filename, `
    <div style="margin-bottom:12px;display:flex;gap:8px">
      <a href="${pdfUrl}" download="${esc(r.filename)}" class="btn btn-secondary btn-sm"><i data-lucide="download"></i> Download PDF</a>
      <button class="btn btn-primary btn-sm" onclick="goTailor(null,'${r.id}');closeModal()"><i data-lucide="wand-2"></i> Tailor to a Job</button>
    </div>
    <iframe src="${pdfUrl}" style="width:100%;height:520px;border:1px solid var(--border);border-radius:8px;background:#fff"></iframe>
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

  const resultHtml = result && result.status === 'completed' ? `
    <div class="tailor-result">
      <div class="tailor-result-header">
        <h3><i data-lucide="sparkles"></i> Tailored Resume PDF</h3>
        <div style="display:flex;gap:8px">
          <a href="${api.tailoredPdfUrl(result.id)}" download="tailored_resume.pdf" class="btn btn-primary btn-sm"><i data-lucide="download"></i> Download PDF</a>
        </div>
      </div>
      <iframe src="${api.tailoredPdfUrl(result.id)}" style="width:100%;height:560px;border:none;border-top:1px solid var(--border)"></iframe>
      <div style="padding:12px 20px;border-top:1px solid var(--border);font-size:.78rem;color:var(--text-muted);display:flex;gap:16px">
        <span>Model: <b>${result.model_used}</b></span>
        ${result.tokens_used ? `<span>Tokens used: <b>${result.tokens_used.toLocaleString()}</b></span>` : ''}
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
  setLoading(btn, true, 'AI is analysing your resume…');

  try {
    const preview = await api.tailor(state.selectedJobId, state.selectedResumeId);
    setLoading(btn, false, null, 'Generate Tailored Resume', 'wand-2');
    showTailorDiff(preview);
  } catch (e) {
    toast(e.message, 'error');
    setLoading(btn, false, null, 'Generate Tailored Resume', 'wand-2');
  }
}

function showTailorDiff(preview) {
  let changes = [], fullTailoredText = '';
  try {
    const parsed = JSON.parse(preview.output_text || '{}');
    changes = parsed.changes || [];
    fullTailoredText = parsed.full_tailored_text || '';
  } catch (_) {}

  if (changes.length === 0) {
    openModal('Review & Edit Resume', `
      <p style="font-size:.875rem;color:var(--text-muted);margin-bottom:10px">
        No section changes were needed — your resume already matches this JD well.<br>
        You can still edit the full text below before generating.
      </p>
      <textarea id="full-resume-text" style="width:100%;height:340px;font-size:.82rem;line-height:1.6;border:1px solid var(--border);border-radius:6px;padding:10px;font-family:monospace;resize:vertical;box-sizing:border-box;background:var(--bg);color:var(--text)">${esc(fullTailoredText)}</textarea>
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
        <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="btn-apply-tailor" onclick="applyTailorChanges('${preview.id}',[])">
          <i data-lucide="check"></i> Generate PDF & DOCX
        </button>
      </div>
    `);
    window._fullTailoredText = fullTailoredText;
    lucide.createIcons({ nodes: [document.getElementById('modal-overlay')] });
    return;
  }

  const sectionsHtml = changes.map((c, i) => `
    <div id="section-card-${i}" style="margin-bottom:16px;border:2px solid #16a34a;border-radius:8px;overflow:hidden;transition:border-color .2s">
      <div style="display:flex;align-items:center;justify-content:space-between;background:var(--bg);padding:8px 14px">
        <span style="font-weight:600;font-size:.82rem;letter-spacing:.05em;color:var(--accent)">${esc(c.section)}</span>
        <div style="display:flex;gap:6px">
          <button id="accept-btn-${i}" class="btn btn-sm" style="background:#dcfce7;color:#16a34a;border:1px solid #16a34a"
            onclick="setSectionDecision(${i},'accept')">✓ Accept</button>
          <button id="reject-btn-${i}" class="btn btn-sm" style="background:var(--card);color:var(--text-muted);border:1px solid var(--border)"
            onclick="setSectionDecision(${i},'reject')">✗ Reject</button>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr">
        <div style="padding:12px 14px;border-right:1px solid var(--border)">
          <div style="font-size:.7rem;font-weight:700;color:#ef4444;margin-bottom:5px;text-transform:uppercase;letter-spacing:.06em">Current</div>
          <div style="font-size:.8rem;line-height:1.65;color:var(--text-muted);white-space:pre-wrap">${esc(c.original)}</div>
        </div>
        <div style="padding:12px 14px">
          <div style="font-size:.7rem;font-weight:700;color:#16a34a;margin-bottom:5px;text-transform:uppercase;letter-spacing:.06em">AI Suggestion <span style="font-weight:400;color:var(--text-muted);font-size:.68rem;text-transform:none">(editable)</span></div>
          <textarea id="edit-section-${i}" style="width:100%;font-size:.8rem;line-height:1.65;color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px;resize:vertical;background:var(--bg);font-family:inherit;min-height:80px;box-sizing:border-box">${esc(c.tailored)}</textarea>
        </div>
      </div>
    </div>`).join('');

  openModal('Review Changes — Section by Section', `
    <p style="font-size:.85rem;color:var(--text-muted);margin-bottom:14px">
      Accept or reject each section. You can also edit the AI suggestion directly in the right panel.
    </p>
    <div style="max-height:360px;overflow-y:auto;margin-bottom:12px">${sectionsHtml}</div>
    <div style="border-top:1px solid var(--border);padding-top:10px;margin-bottom:12px">
      <button class="btn btn-ghost btn-sm" onclick="toggleFullEditor()" id="toggle-full-editor-btn">
        <i data-lucide="edit-3"></i> Edit Full Resume Text
      </button>
      <div id="full-editor-wrap" style="display:none;margin-top:8px">
        <p style="font-size:.75rem;color:var(--text-muted);margin-bottom:6px">Edit the complete resume text. If you edit here, section Accept/Reject choices above are ignored.</p>
        <textarea id="full-resume-text" style="width:100%;height:280px;font-size:.82rem;line-height:1.6;border:1px solid var(--border);border-radius:6px;padding:10px;font-family:monospace;resize:vertical;box-sizing:border-box;background:var(--bg);color:var(--text)">${esc(fullTailoredText)}</textarea>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap">
      <span id="accepted-count" style="font-size:.8125rem;color:var(--text-muted)">${changes.length} of ${changes.length} accepted</span>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="btn-apply-tailor" onclick="applyTailorChanges('${preview.id}',getTailorDecisions())">
          <i data-lucide="check"></i> Apply & Generate PDF + DOCX
        </button>
      </div>
    </div>
  `);

  // Store decisions (all accepted by default)
  window._tailorDecisions = changes.map((c, i) => ({ index: i, section: c.section, tailored: c.tailored, accepted: true }));
  window._fullTailoredText = fullTailoredText;
  lucide.createIcons({ nodes: [document.getElementById('modal-overlay')] });
}

function setSectionDecision(idx, decision) {
  window._tailorDecisions[idx].accepted = (decision === 'accept');

  const card = document.getElementById(`section-card-${idx}`);
  const acceptBtn = document.getElementById(`accept-btn-${idx}`);
  const rejectBtn = document.getElementById(`reject-btn-${idx}`);

  if (decision === 'accept') {
    card.style.borderColor = '#16a34a';
    acceptBtn.style.cssText = 'background:#dcfce7;color:#16a34a;border:1px solid #16a34a';
    rejectBtn.style.cssText = 'background:var(--card);color:var(--text-muted);border:1px solid var(--border)';
  } else {
    card.style.borderColor = '#ef4444';
    rejectBtn.style.cssText = 'background:#fee2e2;color:#ef4444;border:1px solid #ef4444';
    acceptBtn.style.cssText = 'background:var(--card);color:var(--text-muted);border:1px solid var(--border)';
  }

  const acceptedCount = window._tailorDecisions.filter(d => d.accepted).length;
  const total = window._tailorDecisions.length;
  const counter = document.getElementById('accepted-count');
  if (counter) counter.textContent = `${acceptedCount} of ${total} accepted`;
}

function toggleFullEditor() {
  const wrap = document.getElementById('full-editor-wrap');
  const btn = document.getElementById('toggle-full-editor-btn');
  const isVisible = wrap.style.display !== 'none';
  wrap.style.display = isVisible ? 'none' : 'block';
  btn.innerHTML = isVisible
    ? '<i data-lucide="edit-3"></i> Edit Full Resume Text'
    : '<i data-lucide="x"></i> Hide Full Editor';
  lucide.createIcons({ nodes: [btn] });
}

function getTailorDecisions() {
  return (window._tailorDecisions || []).filter(d => d.accepted).map(d => {
    const ta = document.getElementById(`edit-section-${d.index}`);
    return { section: d.section, tailored: ta ? ta.value : d.tailored };
  });
}

async function applyTailorChanges(previewId, decisions) {
  // decisions is either [] (no-diff path) or [{section, tailored}] objects
  const decisionArr = Array.isArray(decisions) ? decisions : [];

  // Check if user opened and edited the full-text editor
  const fullEditorWrap = document.getElementById('full-editor-wrap');
  const fullTextEl = document.getElementById('full-resume-text');
  const fullEditorOpen = fullEditorWrap && fullEditorWrap.style.display !== 'none';
  const fullTextOverride = (fullEditorOpen && fullTextEl && fullTextEl.value.trim())
    ? fullTextEl.value.trim() : null;

  // If not using full editor and no sections accepted, warn
  if (!fullTextOverride && decisionArr.length === 0 && window._tailorDecisions?.length > 0) {
    toast('Please accept at least one section, or use the full text editor.', 'error');
    return;
  }

  const btn = document.getElementById('btn-apply-tailor');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Generating…'; }

  try {
    const result = await api.applyTailor(previewId, decisionArr, fullTextOverride);
    closeModal();
    toast('Resume tailored and PDF generated!', 'success');
    // Refresh jobs page so tailored section updates
    if (state.page === 'jobs') {
      const data = await api.getJobs(0, 200);
      state.jobs = data.items;
      state.jobsTotal = data.total;
      renderJobsUI();
    }
  } catch (e) {
    toast(e.message, 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="check"></i> Apply Selected & Generate PDF'; lucide.createIcons({nodes:[btn]}); }
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
    const pdfUrl = api.tailoredPdfUrl(id);
    openModal('Tailored Resume', `
      <div style="margin-bottom:12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span class="badge badge-${t.status}">${t.status}</span>
        <span style="font-size:.8rem;color:var(--text-muted)">Model: ${t.model_used}</span>
        ${t.tokens_used ? `<span style="font-size:.8rem;color:var(--text-muted)">${t.tokens_used.toLocaleString()} tokens</span>` : ''}
        <a href="${pdfUrl}" download="tailored_resume.pdf" class="btn btn-primary btn-sm" style="margin-left:auto">
          <i data-lucide="download"></i> Download PDF
        </a>
      </div>
      ${t.status === 'completed' && t.output_path
        ? `<iframe src="${pdfUrl}" style="width:100%;height:520px;border:1px solid var(--border);border-radius:8px;background:#fff"></iframe>`
        : `<div style="white-space:pre-wrap;font-size:.8125rem;line-height:1.75;color:var(--text);background:#f8fafc;padding:16px;border-radius:8px;max-height:440px;overflow-y:auto">${esc(t.error_msg || 'PDF not available.')}</div>`
      }
    `);
  } catch (e) {
    toast(e.message, 'error');
  }
}

/* =============================================
   HELPERS
   ============================================= */
async function goTailor(jobId = null) {
  const job = state.jobs.find(j => j.id === jobId);
  if (!job) return;

  // Ensure resumes are loaded
  if (!state.resumes.length) {
    try { const d = await api.getResumes(); state.resumes = d.items; } catch (_) {}
  }

  const resumeListHtml = state.resumes.length === 0
    ? `<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:.875rem">
        No resumes uploaded yet.
        <br><button class="btn btn-primary btn-sm" style="margin-top:10px" onclick="navigate('resumes');closeModal()">Upload Resume</button>
       </div>`
    : state.resumes.map(r => `
        <div class="selector-item ${r.id === state.selectedResumeId ? 'selected' : ''}"
             onclick="selectTailorResume('${r.id}',this)"
             style="padding:10px 14px;border-radius:8px;cursor:pointer;border:2px solid ${r.id === state.selectedResumeId ? 'var(--accent)' : 'var(--border)'};margin-bottom:8px;transition:border-color .15s">
          <div style="font-weight:500;font-size:.875rem">${esc(r.label || r.filename)}</div>
          <div style="font-size:.75rem;color:var(--text-muted)">${esc(r.filename)} · ${new Date(r.created_at).toLocaleDateString()}</div>
        </div>`).join('');

  openModal(`Tailor Resume — ${esc(job.title)}`, `
    <p style="font-size:.85rem;color:var(--text-muted);margin-bottom:12px">
      Select the resume you want to tailor for <strong>${esc(job.title)}</strong> at <strong>${esc(job.company || '—')}</strong>.
    </p>
    <div style="max-height:300px;overflow-y:auto;margin-bottom:14px">${resumeListHtml}</div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="btn-start-tailor" onclick="startTailorFromModal('${jobId}')" ${state.selectedResumeId ? '' : 'disabled'} style="${state.selectedResumeId ? '' : 'opacity:.5'}">
        <i data-lucide="wand-2"></i> Tailor with AI
      </button>
    </div>
  `);
  lucide.createIcons({ nodes: [document.getElementById('modal-overlay')] });
}

function selectTailorResume(resumeId, el) {
  state.selectedResumeId = resumeId;
  // Update selection styles
  el.closest('.modal-body').querySelectorAll('[onclick^="selectTailorResume"]').forEach(card => {
    card.style.borderColor = 'var(--border)';
  });
  el.style.borderColor = 'var(--accent)';
  const btn = document.getElementById('btn-start-tailor');
  if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
}

async function startTailorFromModal(jobId) {
  if (!state.selectedResumeId) return;
  const btn = document.getElementById('btn-start-tailor');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> AI is analysing…'; }

  try {
    const preview = await api.tailor(jobId, state.selectedResumeId);
    closeModal();
    // Refresh job list so the tailored section shows updated count
    const data = await api.getJobs(0, 200);
    state.jobs = data.items;
    state.jobsTotal = data.total;
    renderJobsUI();
    showTailorDiff(preview);
  } catch (e) {
    toast(e.message, 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="wand-2"></i> Tailor with AI'; lucide.createIcons({ nodes: [btn] }); }
  }
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

function formatJobDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d)) return '—';
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
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
