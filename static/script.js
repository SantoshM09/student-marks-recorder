function searchTable() {
    const input = (document.getElementById('search')?.value || '').toLowerCase();
    // Support both old id #marksTable and new #studentsTable
    const table = document.getElementById('studentsTable') || document.getElementById('marksTable');
    if (!table) return;
    const rows = table.querySelectorAll('tbody tr');
    const matches = [];
    rows.forEach((row, idx) => {
        const cells = Array.from(row.getElementsByTagName('td')).map(td => (td.textContent || '').toLowerCase());
        const text = cells.join(' ');
        const isMatch = input.length === 0 ? true : text.includes(input);
        row.style.display = isMatch ? '' : 'none';
        if (isMatch && input.length > 0) {
            const display = Array.from(row.getElementsByTagName('td')).map(td => (td.textContent || '').trim());
            matches.push({
                row: row,
                roll: display[0] || '',
                name: display[1] || '',
                email: display[2] || '',
                subject: display[3] || '',
                marks: display[4] || '',
                grade: display[5] || ''
            });
        }
    });

    renderSearchResults(matches, input);
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
    if (!query || matches.length === 0) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    const maxItems = 10;
    container.innerHTML = '';
    matches.slice(0, maxItems).forEach((m, i) => {
        const item = document.createElement('a');
        item.href = 'javascript:void(0)';
        item.className = 'list-group-item list-group-item-action small opacity-75';
        item.innerHTML = `${m.roll} — <strong>${m.name}</strong> | ${m.email} | ${m.subject} | Marks: ${m.marks} | Grade: ${m.grade}`;
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
    row.style.backgroundColor = '#fff3cd';
    setTimeout(() => {
        row.style.backgroundColor = original || '';
    }, 1200);
}
