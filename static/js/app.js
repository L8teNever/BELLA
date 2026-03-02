// Docker Container Backup Manager - Frontend JavaScript

// Global state
const state = {
    containers: [],
    backups: [],
    schedules: [],
    currentTab: 'containers',
};

// API base URL
const API_BASE = '/api';

// ============================================================================
// Utility Functions
// ============================================================================

function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    container.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('de-DE') + ' ' + date.toLocaleTimeString('de-DE');
}

async function apiCall(method, endpoint, data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(API_BASE + endpoint, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || result.message || 'API Error');
        }

        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ============================================================================
// Docker Containers
// ============================================================================

async function loadContainers() {
    try {
        const containers = await apiCall('GET', '/containers');
        state.containers = containers;
        renderContainers();
    } catch (error) {
        showNotification(`Fehler beim Laden der Container: ${error.message}`, 'error');
    }
}

function renderContainers() {
    const container = document.getElementById('containers-list');

    if (state.containers.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 40px;">Keine Container gefunden</p>';
        return;
    }

    container.innerHTML = state.containers.map(cont => `
        <div class="container-card">
            <div class="container-card-header">
                <h3 class="container-name">${cont.name}</h3>
                <span class="container-status ${cont.status.toLowerCase()}">
                    ${cont.status}
                </span>
            </div>
            <div class="container-info">
                <div class="container-info-item">
                    <span class="container-info-label">Image:</span>
                    <span class="container-info-value">${cont.image}</span>
                </div>
                <div class="container-info-item">
                    <span class="container-info-label">ID:</span>
                    <span class="container-info-value">${cont.id}</span>
                </div>
                <div class="container-info-item">
                    <span class="container-info-label">Volumes:</span>
                    <span class="container-info-value">${cont.volumes.length > 0 ? cont.volumes.length : 'Keine'}</span>
                </div>
                <div class="container-info-item">
                    <span class="container-info-label">Erstellt:</span>
                    <span class="container-info-value">${formatDate(cont.created_at)}</span>
                </div>
            </div>
            <div class="container-actions">
                <button class="btn-primary" onclick="createBackupForContainer('${cont.id}', '${cont.name}')">
                    Backup erstellen
                </button>
                <button class="btn-secondary" onclick="showContainerLogs('${cont.id}')">
                    Logs
                </button>
            </div>
        </div>
    `).join('');
}

function updateScheduleContainer() {
    const select = document.getElementById('schedule-container');
    select.innerHTML = '<option value="">-- Bitte wählen --</option>' +
        state.containers.map(cont =>
            `<option value="${cont.id}">${cont.name}</option>`
        ).join('');
}

async function createBackupForContainer(containerId, containerName) {
    try {
        showNotification(`Erstelle Backup für ${containerName}...`, 'info');

        const response = await apiCall('POST', `/containers/${containerId}/backup`, {
            include_volumes: true,
            include_config: true,
            include_database: true,
            include_image: false,
        });

        showNotification(`Backup erstellt: ${response.data.filename}`, 'success');
        await loadBackups();
    } catch (error) {
        showNotification(`Fehler beim Erstellen des Backups: ${error.message}`, 'error');
    }
}

async function showContainerLogs(containerId) {
    try {
        const response = await apiCall('GET', `/containers/${containerId}/logs`);
        alert(response.data.logs || 'Keine Logs verfügbar');
    } catch (error) {
        showNotification(`Fehler beim Laden der Logs: ${error.message}`, 'error');
    }
}

// ============================================================================
// Backups
// ============================================================================

async function loadBackups() {
    try {
        const backups = await apiCall('GET', '/backups');
        state.backups = backups;

        // Load stats
        const stats = await apiCall('GET', '/backups/stats');
        updateBackupStats(stats.data);

        renderBackups();
    } catch (error) {
        showNotification(`Fehler beim Laden der Backups: ${error.message}`, 'error');
    }
}

function updateBackupStats(stats) {
    document.getElementById('backup-count').textContent = stats.total_backups;
    document.getElementById('backup-size').textContent = stats.total_size_gb + ' GB';
    document.getElementById('oldest-backup').textContent = stats.oldest_backup
        ? formatDate(stats.oldest_backup)
        : '-';
    document.getElementById('newest-backup').textContent = stats.newest_backup
        ? formatDate(stats.newest_backup)
        : '-';
}

function renderBackups() {
    const container = document.getElementById('backups-list');

    if (state.backups.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 40px;">Keine Backups vorhanden</p>';
        return;
    }

    const headerHtml = `
        <div class="table-header">
            <div>Dateiname</div>
            <div>Größe</div>
            <div>Container</div>
            <div>Erstellt</div>
            <div>Inhalte</div>
            <div>Aktionen</div>
        </div>
    `;

    const rowsHtml = state.backups.map(backup => `
        <div class="table-row">
            <div>${backup.filename}</div>
            <div>${formatBytes(backup.size)}</div>
            <div>${backup.container_name}</div>
            <div>${formatDate(backup.created_at)}</div>
            <div>${backup.includes.join(', ')}</div>
            <div class="table-actions">
                <button class="btn-primary" onclick="downloadBackup('${backup.filename}')">
                    Download
                </button>
                <button class="btn-secondary" onclick="showRestoreModal('${backup.filename}')">
                    Restore
                </button>
                <button class="btn-danger" onclick="deleteBackup('${backup.filename}')">
                    Löschen
                </button>
            </div>
        </div>
    `).join('');

    container.innerHTML = headerHtml + rowsHtml;
}

async function downloadBackup(filename) {
    try {
        window.location.href = `${API_BASE}/backups/${filename}/download`;
        showNotification('Download gestartet...', 'success');
    } catch (error) {
        showNotification(`Fehler beim Download: ${error.message}`, 'error');
    }
}

function showRestoreModal(filename) {
    document.getElementById('restore-filename').value = filename;
    document.getElementById('restore-modal').classList.remove('hidden');
}

async function deleteBackup(filename) {
    if (!confirm(`Möchtest du das Backup "${filename}" wirklich löschen?`)) {
        return;
    }

    try {
        await apiCall('DELETE', `/backups/${filename}`);
        showNotification('Backup gelöscht', 'success');
        await loadBackups();
    } catch (error) {
        showNotification(`Fehler beim Löschen: ${error.message}`, 'error');
    }
}

// ============================================================================
// Schedules
// ============================================================================

async function loadSchedules() {
    try {
        const response = await apiCall('GET', '/schedules');
        state.schedules = response.data || [];
        renderSchedules();
    } catch (error) {
        showNotification(`Fehler beim Laden der Zeitpläne: ${error.message}`, 'error');
    }
}

function renderSchedules() {
    const container = document.getElementById('schedules-list');

    if (state.schedules.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 40px;">Keine Zeitpläne vorhanden</p>';
        return;
    }

    const headerHtml = `
        <div class="table-header">
            <div>Container</div>
            <div>Cron Expression</div>
            <div>Nächster Backup</div>
            <div>Letzter Backup</div>
            <div>Erstellt</div>
            <div>Aktionen</div>
        </div>
    `;

    const rowsHtml = state.schedules.map(schedule => `
        <div class="table-row">
            <div>${schedule.container_name}</div>
            <div><code>${schedule.cron_expression}</code></div>
            <div>${schedule.next_run_time ? formatDate(schedule.next_run_time) : '-'}</div>
            <div>${schedule.last_run_time ? formatDate(schedule.last_run_time) : '-'}</div>
            <div>${formatDate(schedule.created_at)}</div>
            <div class="table-actions">
                <button class="btn-primary" onclick="triggerSchedule('${schedule.job_id}')">
                    Jetzt ausführen
                </button>
                <button class="btn-danger" onclick="deleteSchedule('${schedule.job_id}')">
                    Löschen
                </button>
            </div>
        </div>
    `).join('');

    container.innerHTML = headerHtml + rowsHtml;
}

async function triggerSchedule(jobId) {
    try {
        showNotification('Führe Zeitplan aus...', 'info');
        await apiCall('POST', `/schedules/${jobId}/trigger`);
        showNotification('Zeitplan ausgeführt', 'success');
        await loadSchedules();
        await loadBackups();
    } catch (error) {
        showNotification(`Fehler: ${error.message}`, 'error');
    }
}

async function deleteSchedule(jobId) {
    if (!confirm('Möchtest du diesen Zeitplan wirklich löschen?')) {
        return;
    }

    try {
        await apiCall('DELETE', `/schedules/${jobId}`);
        showNotification('Zeitplan gelöscht', 'success');
        await loadSchedules();
    } catch (error) {
        showNotification(`Fehler beim Löschen: ${error.message}`, 'error');
    }
}

// ============================================================================
// System Info
// ============================================================================

async function loadSystemInfo() {
    try {
        const response = await apiCall('GET', '/info');
        renderSystemInfo(response.data);
    } catch (error) {
        showNotification(`Fehler beim Laden der Systeminformationen: ${error.message}`, 'error');
    }
}

function renderSystemInfo(info) {
    const container = document.getElementById('system-info');

    const dockerStatus = info.docker_connected
        ? '<span style="color: var(--success-color);">✓ Verbunden</span>'
        : '<span style="color: var(--error-color);">✗ Nicht verbunden</span>';

    const html = `
        <div class="info-card">
            <h3>Anwendung</h3>
            <div class="info-item">
                <span class="info-label">Name:</span>
                <span class="info-value">${info.app_name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Version:</span>
                <span class="info-value">${info.app_version}</span>
            </div>
        </div>

        <div class="info-card">
            <h3>Docker</h3>
            <div class="info-item">
                <span class="info-label">Status:</span>
                <span class="info-value">${dockerStatus}</span>
            </div>
        </div>

        <div class="info-card">
            <h3>Scheduler</h3>
            <div class="info-item">
                <span class="info-label">Status:</span>
                <span class="info-value">${info.scheduler.running ? 'Läuft' : 'Gestoppt'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Aktive Jobs:</span>
                <span class="info-value">${info.scheduler.total_jobs}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Zeitzone:</span>
                <span class="info-value">${info.scheduler.timezone}</span>
            </div>
        </div>

        <div class="info-card">
            <h3>Backups</h3>
            <div class="info-item">
                <span class="info-label">Gesamtanzahl:</span>
                <span class="info-value">${info.backup_stats.total_backups}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Speichergröße:</span>
                <span class="info-value">${info.backup_stats.total_size_gb} GB</span>
            </div>
        </div>
    `;

    container.innerHTML = html;

    // Update Docker status badge
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');

    if (info.docker_connected) {
        statusDot.classList.remove('disconnected');
        statusDot.classList.add('connected');
        statusText.textContent = 'Docker verbunden';
    } else {
        statusDot.classList.remove('connected');
        statusDot.classList.add('disconnected');
        statusText.textContent = 'Docker nicht verbunden';
    }
}

// ============================================================================
// Tab Navigation
// ============================================================================

document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', async (e) => {
        const tabName = e.currentTarget.dataset.tab;
        switchTab(tabName);
    });
});

async function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load tab data
    state.currentTab = tabName;

    if (tabName === 'containers') {
        await loadContainers();
    } else if (tabName === 'backups') {
        await loadBackups();
    } else if (tabName === 'schedules') {
        await loadSchedules();
    } else if (tabName === 'info') {
        await loadSystemInfo();
    }
}

// ============================================================================
// Upload Handler
// ============================================================================

const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('backup-file-input');

uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
    }
});

async function uploadFile(file) {
    if (!file.name.endsWith('.zip')) {
        showNotification('Nur ZIP-Dateien sind erlaubt', 'error');
        return;
    }

    try {
        showNotification(`Laden ${file.name}...`, 'info');

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/backups/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Upload fehlgeschlagen');
        }

        showNotification('Backup erfolgreich hochgeladen', 'success');
        await loadBackups();
    } catch (error) {
        showNotification(`Fehler beim Upload: ${error.message}`, 'error');
    }
}

// ============================================================================
// Modal Handlers
// ============================================================================

const scheduleModal = document.getElementById('schedule-modal');
const restoreModal = document.getElementById('restore-modal');
const scheduleForm = document.getElementById('schedule-form');
const restoreForm = document.getElementById('restore-form');

// Close modals
document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.target.closest('.modal').classList.add('hidden');
    });
});

// Add schedule
document.getElementById('add-schedule-btn').addEventListener('click', async () => {
    await loadContainers();
    updateScheduleContainer();
    scheduleModal.classList.remove('hidden');
});

scheduleForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(scheduleForm);
    const data = {
        container_id: document.getElementById('schedule-container').value,
        cron_expression: document.getElementById('schedule-cron').value,
        include_volumes: formData.has('include_volumes'),
        include_config: formData.has('include_config'),
        include_database: formData.has('include_database'),
        include_image: formData.has('include_image'),
    };

    try {
        await apiCall('POST', '/schedules', data);
        showNotification('Zeitplan erstellt', 'success');
        scheduleModal.classList.add('hidden');
        scheduleForm.reset();
        await loadSchedules();
    } catch (error) {
        showNotification(`Fehler: ${error.message}`, 'error');
    }
});

// Restore backup
restoreForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const filename = document.getElementById('restore-filename').value;
    const formData = new FormData(restoreForm);
    const data = {
        backup_filename: filename,
        target_path: document.getElementById('restore-path').value,
        restore_volumes: formData.has('restore_volumes'),
        restore_config: formData.has('restore_config'),
        restore_database: formData.has('restore_database'),
    };

    try {
        showNotification('Stelle Backup wieder her...', 'info');
        await apiCall('POST', `/backups/${filename}/restore`, data);
        showNotification('Backup erfolgreich wiederhergestellt', 'success');
        restoreModal.classList.add('hidden');
        restoreForm.reset();
    } catch (error) {
        showNotification(`Fehler: ${error.message}`, 'error');
    }
});

// Refresh buttons
document.getElementById('refresh-containers').addEventListener('click', loadContainers);
document.getElementById('refresh-backups').addEventListener('click', loadBackups);

// ============================================================================
// Initial Load
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    // Load initial data
    await loadContainers();
    await loadSystemInfo();
});

// Auto-refresh every 30 seconds when on containers tab
setInterval(() => {
    if (state.currentTab === 'containers' || state.currentTab === 'backups') {
        if (state.currentTab === 'containers') loadContainers();
        if (state.currentTab === 'backups') loadBackups();
    }
}, 30000);
