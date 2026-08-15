/* ResearchMate AI - vanilla JavaScript only */

// ---------------------------------------------------------- helpers
function post(url, data) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data || {}),
  }).then(function (r) { return r.json(); });
}

function loadingHTML(text) {
  return '<span class="loading"><span class="spinner"></span>' + text + "</span>";
}

function escapeHTML(str) {
  var d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// ---------------------------------------------------------- upload
var uploadForm = document.getElementById("uploadForm");
if (uploadForm) {
  uploadForm.addEventListener("submit", function (e) {
    var input = document.getElementById("pdfFile");
    var box = document.getElementById("uploadError");
    box.textContent = "";
    var file = input.files[0];
    if (!file) { e.preventDefault(); box.textContent = "Please choose a PDF file."; return; }
    if (!file.name.toLowerCase().endsWith(".pdf")) { e.preventDefault(); box.textContent = "Only PDF files are allowed."; return; }
    if (file.size > 10 * 1024 * 1024) { e.preventDefault(); box.textContent = "File is too large. Maximum size is 10 MB."; return; }
    box.innerHTML = loadingHTML("Uploading and indexing the paper...");
  });
}

// ---------------------------------------------------------- summary
var summaryButton = document.getElementById("summaryButton");
if (summaryButton) {
  summaryButton.addEventListener("click", function () {
    var out = document.getElementById("summaryOutput");
    out.innerHTML = loadingHTML("AI is analyzing the paper...");
    summaryButton.disabled = true;
    post("/api/summarize/" + PAPER_ID).then(function (data) {
      summaryButton.disabled = false;
      out.textContent = data.success ? data.summary : data.error;
    }).catch(function () {
      summaryButton.disabled = false;
      out.textContent = "Unable to generate the summary. Please try again.";
    });
  });
}

// ---------------------------------------------------------- chat
var chatInput = document.getElementById("chatInput");
var chatButton = document.getElementById("chatButton");
var chatMessages = document.getElementById("chatMessages");

function addMessage(role, html) {
  var wrap = document.createElement("div");
  wrap.className = "msg " + role;
  wrap.innerHTML = (role === "ai" ? '<span class="avatar">🤖</span>' : "") +
    '<div class="bubble">' + html + "</div>";
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}

function sendQuestion() {
  var question = chatInput.value.trim();
  if (!question) return;
  addMessage("user", escapeHTML(question));
  chatInput.value = "";
  var pending = addMessage("ai", loadingHTML("ResearchMate is thinking..."));

  post("/api/chat", { paper_id: PAPER_ID, question: question }).then(function (data) {
    if (!data.success) { pending.querySelector(".bubble").textContent = data.error; return; }
    var html = escapeHTML(data.answer);
    if (data.sources && data.sources.length) {
      html += '<div class="sources"><h5>Grounded Sources</h5>';
      data.sources.forEach(function (s) {
        html += '<div class="source"><b>Page ' + s.page + "</b><br>" + escapeHTML(s.text) + "…</div>";
      });
      html += "</div>";
    }
    pending.querySelector(".bubble").innerHTML = html;
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }).catch(function () {
    pending.querySelector(".bubble").textContent = "Unable to generate the answer. Please try again.";
  });
}

if (chatButton) {
  chatButton.addEventListener("click", sendQuestion);
  chatInput.addEventListener("keydown", function (e) { if (e.key === "Enter") sendQuestion(); });
  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () { chatInput.value = chip.textContent; sendQuestion(); });
  });
}

// ---------------------------------------------------------- search
var searchButton = document.getElementById("searchButton");
if (searchButton) {
  var runSearch = function () {
    var query = document.getElementById("searchInput").value.trim();
    var box = document.getElementById("searchResults");
    if (!query) { box.innerHTML = '<p class="error-text">Please enter a search term.</p>'; return; }
    box.innerHTML = loadingHTML("Searching research content...");
    post("/api/search", { paper_id: PAPER_ID, query: query }).then(function (data) {
      if (!data.success) { box.innerHTML = '<p class="error-text">' + data.error + "</p>"; return; }
      if (!data.results.length) { box.innerHTML = '<p class="muted">No relevant information found in this paper.</p>'; return; }
      box.innerHTML = data.results.map(function (r) {
        return '<div class="result-item"><span class="score">Similarity: ' + r.score +
          '</span><b>Page ' + r.page + "</b><p>" + escapeHTML(r.text.slice(0, 300)) + "…</p></div>";
      }).join("");
    }).catch(function () { box.innerHTML = '<p class="error-text">Search failed. Please try again.</p>'; });
  };
  searchButton.addEventListener("click", runSearch);
  document.getElementById("searchInput").addEventListener("keydown", function (e) {
    if (e.key === "Enter") runSearch();
  });
}

// ---------------------------------------------------------- delete
function deletePaper(id) {
  if (!confirm("Delete this paper and all its indexed content?")) return;
  post("/api/delete/" + id).then(function () { window.location.href = "/library"; });
}

// ---------------------------------------------------------- compare
var compareButton = document.getElementById("compareButton");
if (compareButton) {
  compareButton.addEventListener("click", function () {
    var a = document.getElementById("compareA").value;
    var b = document.getElementById("compareB").value;
    var box = document.getElementById("compareResult");
    if (a === b) { box.textContent = "Please select two different papers."; return; }
    box.innerHTML = loadingHTML("Comparing the two papers...");
    post("/api/compare", { paper_ids: [parseInt(a), parseInt(b)] }).then(function (data) {
      box.textContent = data.success ? data.comparison : data.error;
    }).catch(function () { box.textContent = "Comparison failed. Please try again."; });
  });
}
