document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    let requestedProfileFromUrl = (urlParams.get('profile') || '').trim();
    const scheduleSource = (urlParams.get('from') || '').trim().toLowerCase();
    const dutIdFromUrl = (urlParams.get('dut_id') || '').trim();

    // Resolve current platform from sessionStorage first, then refresh from server sysinfo
    let currentPlatform = (sessionStorage.getItem('selectedPlatform') || '').trim();

    const titleDisplay = document.getElementById('profile-title-display');
    const subtitleDisplay = document.getElementById('profile-schedule-display');

    function scheduleApiUrl(path) {
        if (scheduleSource === 'monitor' && dutIdFromUrl) {
            const separator = path.includes('?') ? '&' : '?';
            return `${path}${separator}dut_id=${encodeURIComponent(dutIdFromUrl)}`;
        }
        return path;
    }

    function applyPlatformName(platformName) {
        const normalized = (platformName || '').trim();
        if (!normalized || normalized.toLowerCase() === 'unknown') return;

        currentPlatform = normalized;
        sessionStorage.setItem('selectedPlatform', currentPlatform);

        if (titleDisplay) {
            titleDisplay.innerText = `${currentPlatform} Daily Schedule`;
        }

        if (subtitleDisplay && subtitleDisplay.innerText.includes('Alpha_1')) {
            subtitleDisplay.innerText = subtitleDisplay.innerText.replace('Alpha_1', currentPlatform);
        }
    }

    if (currentPlatform) {
        applyPlatformName(currentPlatform);
    }

    async function resolveMonitorContextProfile() {
        if (scheduleSource !== 'monitor' || !dutIdFromUrl) {
            return;
        }

        try {
            const response = await fetch(`/api/lab_monitor/dut/${encodeURIComponent(dutIdFromUrl)}/schedule`);
            const data = await response.json();

            if (data.success && data.schedule) {
                const dutProfile = (data.schedule.profile_name || '').trim();
                if (dutProfile && !requestedProfileFromUrl) {
                    requestedProfileFromUrl = dutProfile;
                }
            }
        } catch (error) {
            console.error('Failed to resolve monitor DUT schedule context:', error);
        }
    }

    await resolveMonitorContextProfile();

    // 1. Initialize Timeline Axis (00:00 to 24:00)
    const timeAxis = document.getElementById('time-axis');
    const startHour = 0;
    const endHour = 24;
    const totalHours = endHour - startHour;
    const pixelsPerHour = 100; // Scale: 100px = 1 hour
    const snapPixels = pixelsPerHour / 2; // 30 minutes snap interval (50px)

    // Set track width based on total hours
    const trackWidth = totalHours * pixelsPerHour;
    const track = document.getElementById('main-track');
    track.style.width = `${trackWidth}px`;
    timeAxis.style.width = `${trackWidth}px`;

    const axisCurrentTimeLine = document.createElement('div');
    axisCurrentTimeLine.className = 'current-time-line current-time-line-axis';
    timeAxis.appendChild(axisCurrentTimeLine);

    const trackCurrentTimeLine = document.createElement('div');
    trackCurrentTimeLine.className = 'current-time-line current-time-line-track';
    track.appendChild(trackCurrentTimeLine);

    function updateCurrentTimeLine() {
        const now = new Date();
        const minutesFromMidnight = (now.getHours() * 60) + now.getMinutes();
        const leftPx = (minutesFromMidnight / 60) * pixelsPerHour;
        const clampedLeft = Math.max(0, Math.min(trackWidth, leftPx));

        axisCurrentTimeLine.style.left = `${clampedLeft}px`;
        trackCurrentTimeLine.style.left = `${clampedLeft}px`;
    }

    updateCurrentTimeLine();
    setInterval(updateCurrentTimeLine, 60000);

    for (let i = 0; i <= totalHours; i++) {
        // Hour marker
        const tickHour = document.createElement('div');
        tickHour.className = 'time-tick hour-tick';
        tickHour.style.left = `${i * pixelsPerHour}px`;
        const hour = (startHour + i).toString().padStart(2, '0');
        if (i < totalHours) {
            tickHour.innerText = `${hour}:00`;
            timeAxis.appendChild(tickHour);
        }

        // Half-hour visual marker
        if (i < totalHours) {
            const tickHalf = document.createElement('div');
            tickHalf.className = 'time-tick half-tick';
            tickHalf.style.left = `${(i * pixelsPerHour) + snapPixels}px`;
            tickHalf.innerText = `${hour}:30`;
            tickHalf.style.fontSize = '0.65rem';
            tickHalf.style.opacity = '0.5';
            tickHalf.style.borderLeftStyle = 'dashed';
            timeAxis.appendChild(tickHalf);
        }
    }
    // Removed current date display as it's not in the new layout
    // 2. Drag & Drop from Library to Track Logic
    let draggedData = null;

    async function loadTestProcedures() {
        const testPalette = document.getElementById('test-palette');
        if (!testPalette) return;

        try {
            const response = await fetch('/api/test/procedures');
            const data = await response.json();

            // Expected response format: {"procedures": ["name1", "name2"]}
            const procedures = data.procedures || [];
            testPalette.innerHTML = '';

            if (procedures.length === 0) {
                testPalette.innerHTML = '<div style="padding:10px; color:var(--text-muted); text-align:center; font-size:0.9rem;">No procedures found.</div>';
                return;
            }

            const types = ['cron', 'event', 'single'];

            procedures.forEach((procName, index) => {
                const type = types[index % types.length];
                const durationMins = 60; // Default placeholder duration

                const itemDiv = document.createElement('div');
                itemDiv.className = `test-item ${type}-trigger`;
                itemDiv.draggable = true;
                itemDiv.dataset.type = type;
                itemDiv.dataset.duration = durationMins;

                itemDiv.innerHTML = `
                    <div class="title">${procName}</div>
                    <div class="meta">Procedure • ${durationMins} mins</div>
                `;

                itemDiv.addEventListener('dragstart', (e) => {
                    let dMins = parseInt(itemDiv.dataset.duration);
                    dMins = Math.ceil(dMins / 30) * 30;

                    draggedData = {
                        title: itemDiv.querySelector('.title').innerText,
                        type: itemDiv.dataset.type,
                        duration: dMins,
                        width: (dMins / 60) * pixelsPerHour
                    };
                    e.dataTransfer.effectAllowed = 'copy';
                });

                testPalette.appendChild(itemDiv);
            });
        } catch (error) {
            console.error("Failed to load test procedures:", error);
            testPalette.innerHTML = '<div style="padding:10px; color:#e74c3c; text-align:center; font-size:0.9rem;">Failed to load.</div>';
        }
    }

    // Initialize list of procedures on the left
    loadTestProcedures();

    // --- Load Profile Logic ---
    const loadProfileSelect = document.getElementById('load-profile-select');
    let loadedProfileName = null;
    let latestExecutionStatus = null;

    function updateLoadedProfileSubtitle() {
        const subtitle = document.getElementById('profile-schedule-display');
        if (!subtitle) return;

        if (!loadedProfileName) {
            subtitle.textContent = 'Unsaved Profile: Drag tests below to build your day.';
            return;
        }

        let subtitleHtml = `Loaded Profile: ${loadedProfileName}`;
        const runningProfile = latestExecutionStatus?.profile_name;
        const runningTitle = latestExecutionStatus?.current_test_title;
        const isRunning = Boolean(latestExecutionStatus?.running);

        if (isRunning && runningProfile === loadedProfileName && runningTitle) {
            subtitleHtml += ` | <span class="running-hint">Running: ${runningTitle}</span>`;
        }

        subtitle.innerHTML = subtitleHtml;
    }

    function applyExecutionStatusToBlocks() {
        const blocks = Array.from(track.querySelectorAll('.scheduled-block'));
        const runningProfile = latestExecutionStatus?.profile_name;
        const runningTitle = latestExecutionStatus?.current_test_title;
        const isRunning = Boolean(latestExecutionStatus?.running);

        blocks.forEach(block => {
            const blockTitle = block.querySelector('.block-title')?.innerText?.trim();
            const statusEl = block.querySelector('.block-status');
            if (!statusEl) return;

            const isCurrentRunningBlock =
                isRunning &&
                loadedProfileName &&
                runningProfile === loadedProfileName &&
                blockTitle === runningTitle;

            statusEl.innerText = isCurrentRunningBlock ? 'Testing' : 'Scheduled';
            block.classList.toggle('is-testing', isCurrentRunningBlock);
        });

        updateLoadedProfileSubtitle();
    }

    async function loadSavedProfilesList() {
        if (!loadProfileSelect) return;
        try {
            const res = await fetch(scheduleApiUrl('/api/schedule/profiles'));
            const data = await res.json();
            if (data.success && data.profiles) {
                data.profiles.forEach(p => {
                    const option = document.createElement('option');
                    option.value = p.name;
                    option.textContent = p.name;
                    loadProfileSelect.appendChild(option);
                });

                // URL override: /schedule?profile=<name>
                if (requestedProfileFromUrl) {
                    loadProfileSelect.value = requestedProfileFromUrl;
                    if (loadProfileSelect.value === requestedProfileFromUrl) {
                        loadProfileSelect.dispatchEvent(new Event('change'));
                        localStorage.setItem('lastLoadedProfile', requestedProfileFromUrl);
                        return;
                    }
                }

                // --- Auto-Load from LocalStorage ---
                const lastLoaded = localStorage.getItem('lastLoadedProfile');
                if (lastLoaded) {
                    loadProfileSelect.value = lastLoaded;
                    if (loadProfileSelect.value === lastLoaded) {
                        loadProfileSelect.dispatchEvent(new Event('change'));
                    } else {
                        // Profile no longer exists on server
                        localStorage.removeItem('lastLoadedProfile');
                    }
                }
            }
        } catch (e) {
            console.error("Failed to load profiles list", e);
        }
    }
    loadSavedProfilesList();

    if (loadProfileSelect) {
        loadProfileSelect.addEventListener('change', async (e) => {
            const profileName = e.target.value;
            const deleteBtn = document.getElementById('btn-delete-profile');
            loadedProfileName = profileName || null;

            if (!profileName) {
                localStorage.removeItem('lastLoadedProfile');
                if (deleteBtn) deleteBtn.style.display = 'none';
                applyExecutionStatusToBlocks();
                return;
            }

            try {
                const encodedName = encodeURIComponent(profileName).replace(/%2F/g, '/');
                const res = await fetch(scheduleApiUrl(`/api/schedule/profiles/${encodedName}`));
                const data = await res.json();

                if (data.success && data.data && data.data.tests) {
                    // Clear existing track
                    track.querySelectorAll('.scheduled-block').forEach(b => b.remove());

                    // Render new blocks
                    data.data.tests.forEach(test => {
                        const widthPx = (test.durationMinutes / 60) * pixelsPerHour;
                        const leftPx = (test.startOffsetMinutes / 60) * pixelsPerHour;

                        const blockData = {
                            title: test.title,
                            type: test.type,
                            width: widthPx
                        };

                        // Call the existing block creation function
                        createScheduledBlock(blockData, leftPx);
                    });

                    // Update profile display visually
                    document.getElementById('modal-profile-name').value = profileName;
                    updateLoadedProfileSubtitle();

                    // Populate recurrence settings in the modal
                    if (data.data.cron_rule && data.data.cron_rule.type) {
                        const ruleType = data.data.cron_rule.type;
                        const freqSelect = document.getElementById('frequency-select');
                        if (freqSelect) {
                            freqSelect.value = ruleType;

                            if (ruleType === 'custom' && data.data.cron_rule.preview) {
                                const customInput = document.getElementById('custom-cron-input');
                                if (customInput) customInput.value = data.data.cron_rule.preview.replace('Cron: ', '').trim();
                            } else if (ruleType === 'weekly' && data.data.cron_rule.preview) {
                                const previewStr = data.data.cron_rule.preview.replace('Every:', '').trim();
                                const days = previewStr.split(',').map(d => d.trim());
                                const checkboxes = document.querySelectorAll('.checkbox-group input');
                                checkboxes.forEach(cb => cb.checked = false);
                                checkboxes.forEach(cb => {
                                    const labelText = cb.parentElement.innerText.trim();
                                    if (days.includes(labelText)) {
                                        cb.checked = true;
                                    }
                                });
                            }
                            // Trigger change to update visibility panels
                            freqSelect.dispatchEvent(new Event('change'));
                        }
                    }

                    // Save to local storage and show delete button
                    localStorage.setItem('lastLoadedProfile', profileName);
                    if (deleteBtn) deleteBtn.style.display = 'inline-block';

                    applyExecutionStatusToBlocks();
                }
            } catch (err) {
                console.error("Failed to fetch profile details", err);
                alert("Failed to load profile.");
            }
        });
    }

    // --- Delete Profile Logic ---
    const deleteProfileBtn = document.getElementById('btn-delete-profile');
    if (deleteProfileBtn) {
        deleteProfileBtn.addEventListener('click', async () => {
            const profileName = localStorage.getItem('lastLoadedProfile');
            if (!profileName) return;

            if (!confirm(`Are you sure you want to delete the profile "${profileName}"?\nThis cannot be undone.`)) {
                return;
            }

            const originalText = deleteProfileBtn.innerText;
            deleteProfileBtn.innerText = "Deleting...";
            deleteProfileBtn.disabled = true;

            try {
                const encodedName = encodeURIComponent(profileName).replace(/%2F/g, '/');
                const res = await fetch(scheduleApiUrl(`/api/schedule/profiles/${encodedName}`), {
                    method: 'DELETE'
                });
                const data = await res.json();

                if (data.success) {
                    alert(`Profile "${profileName}" deleted successfully.`);
                    localStorage.removeItem('lastLoadedProfile');
                    window.location.reload();
                } else {
                    alert("Failed to delete profile: " + (data.error || "Unknown error"));
                    deleteProfileBtn.innerText = originalText;
                    deleteProfileBtn.disabled = false;
                }
            } catch (err) {
                console.error("Failed to delete profile", err);
                alert("Error deleting profile.");
                deleteProfileBtn.innerText = originalText;
                deleteProfileBtn.disabled = false;
            }
        });
    }


    track.addEventListener('dragover', (e) => {
        e.preventDefault();
        track.classList.add('drag-over');
    });

    track.addEventListener('dragleave', () => {
        track.classList.remove('drag-over');
    });

    track.addEventListener('drop', (e) => {
        e.preventDefault();
        track.classList.remove('drag-over');

        if (!draggedData) return;

        const trackRect = track.getBoundingClientRect();
        let rawDropX = Math.max(0, e.clientX - trackRect.left);
        let snappedDropX = Math.round(rawDropX / snapPixels) * snapPixels;

        if (snappedDropX + draggedData.width > trackWidth) {
            alert("Not enough time left in the day ⚠️\nThe task exceeds the 24:00 boundary.");
            return;
        }

        if (checkCollision(snappedDropX, draggedData.width, null)) {
            alert("Collision Detected! ⚠️\nTasks on a single machine cannot overlap in time.");
            return;
        }

        createScheduledBlock(draggedData, snappedDropX);
        draggedData = null;
    });

    // Helper to check for horizontal overlaps
    function checkCollision(newStart, newWidth, ignoreBlock) {
        const newEnd = newStart + newWidth;
        const existingBlocks = Array.from(track.querySelectorAll('.scheduled-block'));

        for (const block of existingBlocks) {
            if (block === ignoreBlock) continue;

            const bStart = parseFloat(block.style.left);
            const bWidth = parseFloat(block.style.width);
            const bEnd = bStart + bWidth;

            // Collision condition
            if (newStart < bEnd && newEnd > bStart) {
                return true;
            }
        }
        return false;
    }

    // Helper to update the HH:MM - HH:MM text on a block
    function updateBlockTimeDisplay(block, startX, width) {
        const startMinutes = (startX / pixelsPerHour) * 60;
        const endMinutes = startMinutes + ((width / pixelsPerHour) * 60);

        const formatTime = (totalMins) => {
            const h = Math.floor(startHour + (totalMins / 60));
            const m = Math.floor(totalMins % 60);
            return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
        };
        block.querySelector('.block-time').innerText = `${formatTime(startMinutes)} - ${formatTime(endMinutes)}`;
    }

    // Main factory function for blocks
    function createScheduledBlock(data, xPos) {
        const template = document.getElementById('scheduled-block-template');
        const clone = template.content.cloneNode(true);
        const block = clone.querySelector('.scheduled-block');

        block.dataset.type = data.type;
        block.classList.add(`${data.type}-trigger`);

        block.style.left = `${xPos}px`;
        block.style.width = `${data.width}px`;

        block.querySelector('.block-title').innerText = data.title;
        updateBlockTimeDisplay(block, xPos, data.width);
        block.querySelector('.block-status').innerText = 'Scheduled';

        const deleteBtn = block.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent triggering drag logic on delete
            block.remove();
        });

        // 3. HORIZONTAL DRAGGING & RESIZING LOGIC
        let isDragging = false;
        let isResizing = false;
        let initialMouseX = 0;
        let initialBlockLeft = 0;
        let initialBlockWidth = 0;
        let originalLeft = 0;

        const resizeHandle = block.querySelector('.resize-handle');

        // Mousedown on resize handle
        resizeHandle.addEventListener('mousedown', (e) => {
            e.stopPropagation(); // Prevent block drag
            isResizing = true;
            initialMouseX = e.clientX;
            initialBlockLeft = parseFloat(block.style.left);
            initialBlockWidth = parseFloat(block.style.width);

            block.classList.add('is-resizing');
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'ew-resize';
        });

        // Mousedown on block (Drag)
        block.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('delete-btn') || e.target.classList.contains('resize-handle')) return;

            isDragging = true;
            initialMouseX = e.clientX;
            initialBlockLeft = parseFloat(block.style.left);
            originalLeft = initialBlockLeft;

            block.classList.add('is-dragging');
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const dx = e.clientX - initialMouseX;
                let newRawLeft = initialBlockLeft + dx;

                if (newRawLeft < 0) newRawLeft = 0;
                if (newRawLeft + data.width > trackWidth) newRawLeft = trackWidth - data.width;

                let snappedLeft = Math.round(newRawLeft / snapPixels) * snapPixels;

                if (!checkCollision(snappedLeft, data.width, block)) {
                    block.style.left = `${snappedLeft}px`;
                    updateBlockTimeDisplay(block, snappedLeft, data.width);
                }
            } else if (isResizing) {
                const dx = e.clientX - initialMouseX;
                let newRawWidth = initialBlockWidth + dx;

                // Minimum width constraint (30 mins = snapPixels)
                let snappedWidth = Math.max(snapPixels, Math.round(newRawWidth / snapPixels) * snapPixels);

                // Boundary constraint: don't resize past 24:00
                const currentLeft = parseFloat(block.style.left);
                if (currentLeft + snappedWidth > trackWidth) {
                    snappedWidth = trackWidth - currentLeft;
                }

                // Collision constraint: don't resize into the next block
                if (!checkCollision(currentLeft, snappedWidth, block)) {
                    block.style.width = `${snappedWidth}px`;
                    data.width = snappedWidth; // Sync data object
                    data.duration = (snappedWidth / pixelsPerHour) * 60;
                    updateBlockTimeDisplay(block, currentLeft, snappedWidth);
                }
            }
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                block.classList.remove('is-dragging');
                document.body.style.userSelect = '';
            }
            if (isResizing) {
                isResizing = false;
                block.classList.remove('is-resizing');
                document.body.style.userSelect = '';
                document.body.style.cursor = '';
            }
        });

        track.appendChild(block);

        applyExecutionStatusToBlocks();
    }

    // --- MODAL MANAGEMENT LOGIC ---
    const modal = document.getElementById('cron-modal');
    const btnOpenModal = document.getElementById('btn-open-save-modal');
    const btnClose = document.getElementById('close-modal');
    const btnCancel = document.getElementById('cancel-modal');
    const btnSave = document.getElementById('save-modal');

    const freqSelect = document.getElementById('frequency-select');
    const panelWeekly = document.getElementById('panel-weekly');
    const panelCustom = document.getElementById('panel-custom');
    const rulePreviewText = document.getElementById('rule-preview-text');

    // UI elements to update on save
    const profileTitleDisplay = document.getElementById('profile-title-display');
    const profileScheduleDisplay = document.getElementById('profile-schedule-display');

    btnOpenModal.addEventListener('click', openCronModal);

    function openCronModal() {
        const existingBlocks = Array.from(track.querySelectorAll('.scheduled-block'));
        const summaryList = document.getElementById('modal-summary-list');
        const summaryCount = document.getElementById('summary-count');
        const profileNameInput = document.getElementById('modal-profile-name');

        // Clear previous summary
        summaryList.innerHTML = '';
        summaryCount.innerText = existingBlocks.length;

        if (existingBlocks.length === 0) {
            summaryList.innerHTML = '<li style="color: var(--text-muted); padding: 5px 0;">No procedures scheduled. Drag tests to the timeline first.</li>';
        } else {
            // Sort blocks by horizontal position (time)
            existingBlocks.sort((a, b) => parseFloat(a.style.left) - parseFloat(b.style.left));

            existingBlocks.forEach(block => {
                const title = block.querySelector('.block-title').innerText;
                const time = block.querySelector('.block-time').innerText;
                const type = block.dataset.type;

                const li = document.createElement('li');
                li.style.cssText = 'display: flex; justify-content: space-between; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 4px; border-left: 3px solid var(--color-' + type + ');';
                li.innerHTML = `<span><b>${time}</b></span> <span>${title}</span>`;
                summaryList.appendChild(li);
            });
        }

        // Default name if empty
        if (!profileNameInput.value) {
            profileNameInput.value = `Profile ${new Date().toLocaleDateString('en-US')}`;
        }

        // Reset or load existing config (for prototype we just start fresh)
        updateModalPanels();
        updatePreview();

        modal.classList.remove('hidden');
    }

    function closeCronModal() {
        modal.classList.add('hidden');
    }

    freqSelect.addEventListener('change', () => {
        if (freqSelect.value === 'custom') {
            const customInput = document.getElementById('custom-cron-input');
            if (!customInput.value || customInput.value === '* * * * *') {
                const existingBlocks = Array.from(track.querySelectorAll('.scheduled-block'));
                if (existingBlocks.length > 0) {
                    existingBlocks.sort((a, b) => parseFloat(a.style.left) - parseFloat(b.style.left));
                    const firstBlock = existingBlocks[0];
                    const leftPx = parseFloat(firstBlock.style.left) || 0;
                    // Use the globally defined pixelsPerHour instead of querying DOM which might be 0 during modal popup
                    const startMinutes = Math.round((leftPx / pixelsPerHour) * 60);
                    const h = Math.floor(startMinutes / 60);
                    const m = Math.floor(startMinutes % 60);
                    // Ensure valid cron Minute values by snapping to nearest 30 if needed (it should already be snapped)
                    const snappedM = (m >= 15 && m < 45) ? 30 : 0;
                    customInput.value = `${snappedM} ${h} * * *`;
                } else {
                    customInput.value = `0 0 * * *`;
                }
            }
        }
        updateModalPanels();
        updatePreview();
    });

    // Listen to all checkboxes and inputs to live-update preview
    document.querySelector('.checkbox-group').addEventListener('change', updatePreview);
    document.getElementById('custom-cron-input').addEventListener('input', updatePreview);

    function updateModalPanels() {
        panelWeekly.classList.add('hidden');
        panelCustom.classList.add('hidden');

        if (freqSelect.value === 'weekly') {
            panelWeekly.classList.remove('hidden');
        } else if (freqSelect.value === 'custom') {
            panelCustom.classList.remove('hidden');
        }
    }

    function updatePreview() {
        let ruleStr = "Single Run";

        if (freqSelect.value === 'single') {
            ruleStr = "Single Run (Today Only)";
        } else if (freqSelect.value === 'daily') {
            ruleStr = "Every Day (Daily)";
        } else if (freqSelect.value === 'weekly') {
            const checkedBoxes = Array.from(document.querySelectorAll('.checkbox-group input:checked'));
            const checkedLabels = checkedBoxes.map(cb => cb.parentElement.innerText.trim());
            ruleStr = checkedLabels.length > 0 ? `Every: ${checkedLabels.join(', ')}` : "Select at least one day";
        } else if (freqSelect.value === 'monthly') {
            ruleStr = "1st of Every Month";
        } else if (freqSelect.value === 'custom') {
            const customVal = document.getElementById('custom-cron-input').value || "* * * * *";
            ruleStr = `Cron: ${customVal}`;
        }

        rulePreviewText.innerText = ruleStr;
    }

    btnClose.addEventListener('click', closeCronModal);
    btnCancel.addEventListener('click', closeCronModal);

    btnSave.addEventListener('click', async () => {
        const profileName = document.getElementById('modal-profile-name').value || 'Unnamed Profile';

        if (freqSelect.value === 'custom') {
            const customVal = document.getElementById('custom-cron-input').value.trim() || "* * * * *";
            const parts = customVal.split(/\s+/);
            if (parts.length >= 1) {
                const mStr = parts[0];
                const validM = ['0', '30', '*', '0,30', '*/30'];
                if (!validM.includes(mStr)) {
                    alert("Custom Cron minute (M) must follow the half-hour interval logic of the timeline.\nPlease use 0, 30, or *.");
                    return;
                }
            }
        }

        // 1. Gather all scheduled blocks to form the 'tests' array
        const allBlocks = Array.from(track.querySelectorAll('.scheduled-block'));
        const tests = allBlocks.map(block => {
            const leftPx = parseFloat(block.style.left);
            const widthPx = parseFloat(block.style.width);

            // Re-calculate the exact minutes based on UI position
            const startOffsetMinutes = (leftPx / pixelsPerHour) * 60;
            const durationMinutes = (widthPx / pixelsPerHour) * 60;

            return {
                title: block.querySelector('.block-title').innerText,
                type: block.dataset.type,
                startOffsetMinutes: Math.round(startOffsetMinutes),
                durationMinutes: Math.round(durationMinutes)
            };
        });

        // 2. Build the payload
        const payload = {
            profile_name: profileName,
            cron_rule: {
                type: freqSelect.value,
                preview: rulePreviewText.innerText
            },
            tests: tests
        };

        try {
            // Change button text to indicate loading
            const originalText = btnSave.innerText;
            btnSave.innerText = "Saving...";
            btnSave.disabled = true;

            // 3. Send to Backend API
            const response = await fetch(scheduleApiUrl('/api/schedule/profiles'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                // 4. Update the main header to reflect the saved profile and its rule
                profileTitleDisplay.innerText = `Profile: ${profileName}`;
                profileScheduleDisplay.innerText = `Schedule active: ${rulePreviewText.innerText} on ${currentPlatform}`;
                profileScheduleDisplay.style.color = 'var(--color-cron)'; // Make it pop visually

                // 4.1 If opened from Lab Monitor, assign the saved profile back to this DUT
                if (scheduleSource === 'monitor' && dutIdFromUrl) {
                    const assignResponse = await fetch(`/api/lab_monitor/dut/${encodeURIComponent(dutIdFromUrl)}/schedule`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            enabled: true,
                            profile_name: profileName
                        })
                    });

                    const assignResult = await assignResponse.json();
                    if (!assignResult.success) {
                        throw new Error(assignResult.error || 'Failed to assign profile to DUT');
                    }
                }

                // Hide delete/resize handles on blocks to simulate "locked/saved" state
                allBlocks.forEach(b => b.style.pointerEvents = 'none');

                // Change the save button text
                btnOpenModal.innerText = "Edit Daily Profile...";

                closeCronModal();
            } else {
                alert(`Error saving profile: ${result.error}`);
            }
        } catch (error) {
            console.error("Failed to save profile:", error);
            alert("Failed to communicate with the scheduling server.");
        } finally {
            btnSave.innerText = "Save Profile and Assign Rule";
            btnSave.disabled = false;
        }
    });

    // --- REAL-TIME SYSINFO DASHBOARD ---
    async function fetchExecutionStatus() {
        try {
            const response = await fetch(scheduleApiUrl('/api/schedule/execution-status'));
            const data = await response.json();

            if (data.success) {
                latestExecutionStatus = data.status || null;
                applyExecutionStatusToBlocks();
            }
        } catch (err) {
            console.error("Failed to fetch execution status", err);
        }
    }

    async function fetchSysinfo() {
        try {
            const response = await fetch(scheduleApiUrl('/api/schedule/sysinfo'));
            const data = await response.json();

            if (data.success) {
                document.getElementById('machine-name-display').innerText = `Machine: ${data.hostname}`;

                // Keep page title aligned to platform name (not hardcoded Alpha_1)
                applyPlatformName(data.platform);

                // CPU
                document.getElementById('cpu-value').innerText = `${data.cpu_percent}%`;
                document.getElementById('cpu-fill').style.width = `${data.cpu_percent}%`;

                // RAM
                document.getElementById('ram-value').innerText = `${data.mem_used_gb}GB / ${data.mem_total_gb}GB`;
                document.getElementById('ram-fill').style.width = `${data.mem_percent}%`;
            }
        } catch (err) {
            console.error("Failed to fetch sysinfo", err);
        }
    }

    // Fetch immediately on load, then poll every 5 seconds
    fetchSysinfo();
    fetchExecutionStatus();
    setInterval(fetchSysinfo, 5000);
    setInterval(fetchExecutionStatus, 5000);
});
