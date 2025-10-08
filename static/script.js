function searchTable() {
    const input = (document.getElementById('search')?.value || '').toLowerCase();
    const selectedBranch = (document.getElementById('branchFilter')?.value || '').toLowerCase();
    // Support both old id #marksTable and new #studentsTable
    const table = document.getElementById('studentsTable') || document.getElementById('marksTable');
    if (!table) return;
    const rows = table.querySelectorAll('tbody tr');
    const matches = [];
    rows.forEach((row) => {
        const cellsLower = Array.from(row.getElementsByTagName('td')).map(td => (td.textContent || '').toLowerCase());
        const cellsDisplay = Array.from(row.getElementsByTagName('td')).map(td => (td.textContent || '').trim());
        const rowText = cellsLower.join(' ');
        const subjectLower = (cellsLower[3] || '');
        const branchOk = selectedBranch.length === 0 || subjectLower === selectedBranch;
        const searchOk = input.length === 0 || rowText.includes(input);
        const show = branchOk && searchOk;
        row.style.display = show ? '' : 'none';
        if (show && input.length > 0) {
            matches.push({
                row: row,
                roll: cellsDisplay[0] || '',
                name: cellsDisplay[1] || '',
                email: cellsDisplay[2] || '',
                subject: cellsDisplay[3] || '',
                marks: cellsDisplay[4] || '',
                grade: cellsDisplay[5] || ''
            });
        }
    });

    renderSearchResults(matches, input);
}

function applyBranchFilter() {
    // Re-run the combined filter when branch changes
    searchTable();
}

function clearSearch() {
    const input = document.getElementById('search');
    if (input) input.value = '';
    searchTable();
    const results = document.getElementById('searchResults');
    if (results) {
        results.style.display = 'none';
        results.innerHTML = '';
    }
}

function renderSearchResults(matches, query) {
    const container = document.getElementById('searchResults');
    if (!container) return;
    if (!query) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    const maxItems = 10;
    container.innerHTML = '';
    if (matches.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'list-group-item text-muted';
        empty.textContent = 'No data found';
        container.appendChild(empty);
        container.style.display = '';
        return;
    }

    matches.slice(0, maxItems).forEach((m, i) => {
        const item = document.createElement('a');
        item.href = 'javascript:void(0)';
        item.className = 'list-group-item list-group-item-action small opacity-75';
        item.innerHTML = `${highlightText(m.roll, query)} — <strong>${highlightText(m.name, query)}</strong> | ${highlightText(m.email, query)} | ${highlightText(m.subject, query)} | Marks: ${highlightText(m.marks, query)} | Grade: ${highlightText(m.grade, query)}`;
        item.onclick = () => {
            highlightRow(m.row);
        };
        container.appendChild(item);
    });

    if (matches.length > maxItems) {
        const more = document.createElement('div');
        more.className = 'list-group-item text-muted';
        more.textContent = `+ ${matches.length - maxItems} more`;
        container.appendChild(more);
    }

    container.style.display = '';
}

function highlightRow(row) {
    if (!row) return;
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const original = row.style.backgroundColor;
    row.style.transition = 'background-color 0.3s ease';
    row.style.backgroundColor = 'rgba(13, 110, 253, 0.12)';
    setTimeout(() => {
        row.style.backgroundColor = original || '';
    }, 1200);
}

function highlightText(text, query) {
    const safe = escapeHtml(String(text || ''));
    if (!query) return safe;
    try {
        const rx = new RegExp('(' + escapeRegex(query) + ')', 'ig');
        return safe.replace(rx, '<mark>$1</mark>');
    } catch (_) {
        return safe;
    }
}

function escapeRegex(s) {
    return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Realtime validation for Add Student form
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('addStudentForm');
    if (!form) return;

    const rollInput = document.getElementById('roll_number');
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const subjectInput = document.getElementById('subject');
    const marksInput = document.getElementById('marks');
    const gradeInput = document.getElementById('grade');

    const patterns = {
        roll: /^[A-Za-z0-9]{3,15}$/,
        name: /^[A-Za-z ]{2,50}$/,
        subject: /^[A-Za-z ]{2,50}$/,
        grade: /^[A-Za-z][A-Za-z+\-]?$/,
        gmail: /^[A-Za-z0-9._%+-]+@gmail\.com$/
    };

    const validateField = (input, validator) => {
        const value = (input.value || '').trim();
        const ok = validator(value);
        input.classList.toggle('is-invalid', !ok);
        input.classList.toggle('is-valid', ok && value.length > 0);
        return ok;
    };

    const validators = {
        roll: () => validateField(rollInput, v => patterns.roll.test(v)),
        name: () => validateField(nameInput, v => patterns.name.test(v)),
        email: () => validateField(emailInput, v => v.length === 0 || patterns.gmail.test(v)),
        subject: () => validateField(subjectInput, v => patterns.subject.test(v)),
        marks: () => validateField(marksInput, v => /^\d{1,3}$/.test(v) && Number(v) >= 0 && Number(v) <= 100),
        grade: () => validateField(gradeInput, v => v.length === 0 || patterns.grade.test(v))
    };

    [
        [rollInput, 'roll'],
        [nameInput, 'name'],
        [emailInput, 'email'],
        [subjectInput, 'subject'],
        [marksInput, 'marks'],
        [gradeInput, 'grade']
    ].forEach(([el, key]) => {
        if (!el) return;
        el.addEventListener('input', validators[key]);
        el.addEventListener('blur', validators[key]);
    });

    form.addEventListener('submit', (e) => {
        const allOk = Object.values(validators).map(fn => fn()).every(Boolean);
        if (!allOk) {
            e.preventDefault();
            e.stopPropagation();
        }
    });
});
