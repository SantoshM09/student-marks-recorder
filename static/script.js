function searchTable() {
    const input = (document.getElementById('search')?.value || '').toLowerCase();
    // Support both old id #marksTable and new #studentsTable
    const table = document.getElementById('studentsTable') || document.getElementById('marksTable');
    if (!table) return;
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach((row, idx) => {
        const cells = Array.from(row.getElementsByTagName('td')).map(td => (td.textContent || '').toLowerCase());
        const text = cells.join(' ');
        row.style.display = text.includes(input) ? '' : 'none';
    });
}

function clearSearch() {
    const input = document.getElementById('search');
    if (input) input.value = '';
    searchTable();
}
