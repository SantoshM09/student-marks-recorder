function searchTable() {
    let input = document.getElementById("search").value.toLowerCase();
    let rows = document.querySelectorAll("#marksTable tr");
    for (let i = 1; i < rows.length; i++) {
        let name = rows[i].getElementsByTagName("td")[1].textContent.toLowerCase();
        rows[i].style.display = name.includes(input) ? "" : "none";
    }
}
