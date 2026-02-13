let currentUser = null;
let authMode = 'login'; // or 'signup'

// -------- TEXT CONSTANTS --------
const APP_NAME = "MindMate";

const SUBTITLE_TEXT = {
  chat: "Talk to your digital friend about stress, studies, and campus life.",
  academics: "Notices, syllabus, PYQs, and past projects in one place.",
  insights: "Anonymous trends to help faculty support students better.",
  manage: "Edit notices, resources, and academic content visible to students.",
  settings: "Personalize appearance, language, and privacy preferences.",
  profile: "Your basic details and an option to clear chat history.",
};

// -------- AUTH UI --------
function toggleAuthMode() {
  authMode = authMode === 'login' ? 'signup' : 'login';
  const submitText = document.getElementById('auth-submit-text');
  const toggleText = document.getElementById('auth-toggle-text');
  const title = document.querySelector('.login-title');

  if (authMode === 'signup') {
    submitText.textContent = 'Sign up';
    toggleText.textContent = 'Already have an account? Login';
    title.textContent = 'Create your MindMate account';
  } else {
    submitText.textContent = 'Login';
    toggleText.textContent = 'New here? Create account';
    title.textContent = 'Welcome';
  }
}

function loginWith(provider) {
  alert(provider + ' login is not implemented yet. In final version, this will use OAuth.');
}

async function handleAuthSubmit() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value.trim();
  const role = document.getElementById('login-role').value;

  if (!email || !password) {
    alert('Please enter email and password');
    return;
  }

  const endpoint = authMode === 'login' ? '/api/login' : '/api/signup';
  console.log('Sending auth request:', { endpoint, email, password, role });

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, role })
    });

    const data = await res.json();
    if (!data.success) {
      alert(data.error || 'Authentication failed');
      return;
    }

    currentUser = {
      email: email,
      role: data.role,
      name: data.name,
      user_id: data.user_id
    };

    document.getElementById('header-user-info').textContent =
      data.name + ' (' + data.role + ')';

    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app-layout').style.display = 'flex';

    const adminEls = document.querySelectorAll('.admin-only');
    adminEls.forEach(el => {
      el.style.display = data.role === 'admin' ? 'block' : 'none';
    });

    // Load right-panel data
    loadDeadlinesRightPanel();
    // loadNoticesRightPanel?.(); // if you have a similar function later

    switchView('chat', document.querySelector('.nav-item[data-view="chat"]'));
  } catch (err) {
    console.error(err);
    alert('Network error. Please try again.');
  }
}

async function loadAcademicsView() {
  try {
    // Projects
    const projectsRes = await fetch('/api/academic/projects');
    const projectsData = await projectsRes.json();

    // PYQs for DBMS
    const pyqsRes = await fetch('/api/academic/pyqs?subject=DBMS');
    const pyqsData = await pyqsRes.json();

    // Syllabus for DBMS
    const syllabusRes = await fetch('/api/academic/syllabus?subject=DBMS');
    const syllabusData = await syllabusRes.json();

    // Notices
    const noticesRes = await fetch('/api/academic/notices');
    const noticesData = await noticesRes.json();

    // Helplines
    const helplinesRes = await fetch('/api/academic/helplines');
    const helplinesData = await helplinesRes.json();

    const view = document.getElementById('view-academics');
    if (!view) return;

    // Build cards grid
    view.innerHTML = `
      <div class="cards-grid">
        <div class="card" id="card-notices">
          <div class="card-header-main">Notices & announcements</div>
          <div class="card-desc">Latest updates from your university.</div>
          <ul id="academics-notices-list" style="font-size:12px; color:#e5e7eb; list-style:none; margin-top:4px;"></ul>
          <div class="link" onclick="sendQuick('Show me notices')">Ask in chat →</div>
        </div>

        <div class="card" id="card-deadlines">
          <div class="card-header-main">Deadlines</div>
          <div class="card-desc">Keep track of assignments and exams.</div>
          <div style="font-size:12px; color:#9ca3af;">Deadlines integration is pending. You can still ask in chat: "Show my deadlines".</div>
        </div>

        <div class="card" id="card-syllabus">
          <div class="card-header-main">DBMS Syllabus</div>
          <div class="card-desc">Units and topics for DBMS.</div>
          <ul id="academics-syllabus-list" style="font-size:12px; color:#e5e7eb; list-style:none; margin-top:4px;"></ul>
        </div>

        <div class="card" id="card-pyqs">
          <div class="card-header-main">DBMS Previous Year Papers</div>
          <div class="card-desc">Practice from real question papers.</div>
          <ul id="academics-pyqs-list" style="font-size:12px; color:#e5e7eb; list-style:none; margin-top:4px;"></ul>
        </div>

        <div class="card" id="card-projects">
          <div class="card-header-main">Past student projects</div>
          <div class="card-desc">Get ideas by exploring previous work.</div>
          <ul id="academics-projects-list" style="font-size:12px; color:#e5e7eb; list-style:none; margin-top:4px;"></ul>
        </div>

        <div class="card" id="card-helplines">
          <div class="card-header-main">Helplines</div>
          <div class="card-desc">Trusted contacts for mental health support.</div>
          <ul id="academics-helplines-list" style="font-size:12px; color:#e5e7eb; list-style:none; margin-top:4px;"></ul>
        </div>
      </div>
    `;

    // Fill notices
    const noticesUl = document.getElementById('academics-notices-list');
    if (noticesUl) {
      if (!noticesData.items.length) {
        noticesUl.innerHTML = '<li>No notices yet.</li>';
      } else {
        noticesUl.innerHTML = '';
        noticesData.items.forEach(n => {
          const li = document.createElement('li');
          li.textContent = `• ${n.title} – ${n.description}`;
          noticesUl.appendChild(li);
        });
      }
    }

    // Fill syllabus
    const syllabusUl = document.getElementById('academics-syllabus-list');
    if (syllabusUl) {
      if (!syllabusData.items.length) {
        syllabusUl.innerHTML = '<li>No syllabus found for DBMS.</li>';
      } else {
        syllabusUl.innerHTML = '';
        syllabusData.items.forEach(s => {
          const li = document.createElement('li');
          li.textContent = `• ${s.unit}: ${s.topics}`;
          syllabusUl.appendChild(li);
        });
      }
    }

    // Fill PYQs
    const pyqsUl = document.getElementById('academics-pyqs-list');
    if (pyqsUl) {
      if (!pyqsData.items.length) {
        pyqsUl.innerHTML = '<li>No PYQs found for DBMS.</li>';
      } else {
        pyqsUl.innerHTML = '';
        pyqsData.items.forEach(p => {
          const li = document.createElement('li');
          li.textContent = `• ${p.year}: ${p.question}`;
          pyqsUl.appendChild(li);
        });
      }
    }

    // Fill projects
    const projectsUl = document.getElementById('academics-projects-list');
    if (projectsUl) {
      if (!projectsData.items.length) {
        projectsUl.innerHTML = '<li>No projects stored yet.</li>';
      } else {
        projectsUl.innerHTML = '';
        projectsData.items.forEach(pr => {
          const li = document.createElement('li');
          li.textContent = `• ${pr.title} (${pr.domain}, ${pr.difficulty}) – ${pr.description}`;
          projectsUl.appendChild(li);
        });
      }
    }

    // Fill helplines
    const helplinesUl = document.getElementById('academics-helplines-list');
    if (helplinesUl) {
      if (!helplinesData.items.length) {
        helplinesUl.innerHTML = '<li>No helplines stored yet.</li>';
      } else {
        helplinesUl.innerHTML = '';
        helplinesData.items.forEach(h => {
          const li = document.createElement('li');
          li.textContent = `• ${h.name}: ${h.phone} (${h.available_hours})`;
          helplinesUl.appendChild(li);
        });
      }
    }

  } catch (e) {
    console.error('Failed to load academics view', e);
  }
}

async function loadInsightsView() {
  const topIntentsUl = document.getElementById("insights-top-intents");
  const complaintsUl = document.getElementById("insights-complaints-dept");
  const overallEl = document.getElementById("insights-overall");

  if (!topIntentsUl || !complaintsUl || !overallEl) return;

  overallEl.textContent = "Loading...";
  topIntentsUl.innerHTML = "";
  complaintsUl.innerHTML = "";

  try {
    const res = await fetch("/api/insights/overview");
    if (!res.ok) throw new Error("Server error " + res.status);
    const data = await res.json();

    const intents = data.intents || [];
    const complaints = data.complaints_by_department || [];

    // Simple overall metric: total intent messages
    const totalIntentMsgs = intents.reduce((sum, x) => sum + (x.count || 0), 0);
    overallEl.textContent =
      totalIntentMsgs > 0
        ? `Total tagged chat messages: ${totalIntentMsgs}`
        : "Not enough data yet. Students haven’t chatted much so far.";

    // Top intents list
    if (!intents.length) {
      topIntentsUl.innerHTML = "<li>No intent data yet.</li>";
    } else {
      intents.forEach((it) => {
        const li = document.createElement("li");
        li.textContent = `${it.intent}: ${it.count}`;
        topIntentsUl.appendChild(li);
      });
    }

    // Complaints by department
    if (!complaints.length) {
      complaintsUl.innerHTML = "<li>No complaints submitted yet.</li>";
    } else {
      complaints.forEach((c) => {
        const li = document.createElement("li");
        li.textContent = `${c.department}: ${c.count}`;
        complaintsUl.appendChild(li);
      });
    }
  } catch (e) {
    console.error("Failed to load insights:", e);
    overallEl.textContent = "Could not load insights. Please try again later.";
  }
}

async function loadDeadlinesRightPanel() {
  const container = document.getElementById("deadlines-list");
  if (!container) return;

  container.innerHTML = "Loading...";

  try {
    const res = await fetch("/api/deadlines");
    if (!res.ok) throw new Error("Server error " + res.status);
    const data = await res.json();

    const items = data.items || [];

    if (!items.length) {
      container.innerHTML = '<div style="font-size:12px;color:#9ca3af;">No upcoming deadlines found.</div>';
      return;
    }

    container.innerHTML = "";
    items.forEach((d) => {
      const row = document.createElement("div");
      row.className = "deadline-item";

      const labelSpan = document.createElement("span");
      labelSpan.className = "notice-label";
      labelSpan.textContent = d.label;

      const metaSpan = document.createElement("span");
      metaSpan.className = "badge";
      metaSpan.textContent = `${d.due_date} · ${d.type || ""}`.trim();

      row.appendChild(labelSpan);
      row.appendChild(metaSpan);
      container.appendChild(row);
    });
  } catch (e) {
    console.error("Failed to load deadlines:", e);
    container.innerHTML =
      '<div style="font-size:12px;color:#f87171;">Could not load deadlines. Please try again later.</div>';
  }
}

// -------- LOGOUT --------
function handleLogout() {
  currentUser = null;
  document.getElementById('header-user-info').textContent = 'Not logged in';
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('app-layout').style.display = 'none';
}

// -------- NAV / VIEWS --------
function switchView(view, navItem) {
  const views = ["chat", "academics", "insights", "manage", "settings", "profile"];
  views.forEach((v) => {
    const el = document.getElementById(`view-${v}`);
    if (el) el.style.display = v === view ? "block" : "none";
  });

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.remove("active");
  });
  if (navItem) navItem.classList.add("active");

  const titleEl = document.getElementById("center-title");
  const subEl = document.getElementById("center-subtitle");

  if (view === "chat") {
    titleEl.textContent = "Chat";
    subEl.textContent = SUBTITLE_TEXT.chat;
  } else if (view === "academics") {
    titleEl.textContent = "Academics";
    subEl.textContent = SUBTITLE_TEXT.academics;
    loadAcademicsView();
  } else if (view === "insights") {
    titleEl.textContent = "Insights";
    subEl.textContent = SUBTITLE_TEXT.insights;
    loadInsightsView();
  } else if (view === "manage") {
    titleEl.textContent = "Manage content";
    subEl.textContent = SUBTITLE_TEXT.manage;
  } else if (view === "settings") {
    titleEl.textContent = "Settings";
    subEl.textContent = SUBTITLE_TEXT.settings;
  } else if (view === "profile") {
    titleEl.textContent = "Profile";
    subEl.textContent = SUBTITLE_TEXT.profile;
  }
}

// -------- CHAT --------
function appendMessage(text, sender = "bot") {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const row = document.createElement("div");
  row.className = `msg-row ${sender === "user" ? "user" : "bot"}`;

  const bubble = document.createElement("div");
  bubble.className = `msg-bubble ${sender === "user" ? "user" : "bot"}`;
  bubble.textContent = text;

  row.appendChild(bubble);
  container.appendChild(row);

  container.scrollTop = container.scrollHeight;
}

async function handleSend() {
  const input = document.getElementById("chat-input");
  if (!input) return;

  const text = input.value.trim();
  if (!text) return;

  appendMessage(text, "user");
  input.value = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        user_id: currentUser ? currentUser.user_id : null,
      }),
    });

    if (!res.ok) {
      throw new Error("Server error " + res.status);
    }

    const data = await res.json();
    if (!data || data.success === false) {
      throw new Error(data && data.error ? data.error : "Unknown error");
    }

    appendMessage(data.reply, "bot");
    console.log("Chat intent:", data.intent, "mood:", data.mood);
  } catch (err) {
    console.error("Chat error:", err);
    appendMessage(
      "Sorry, I had trouble reaching the server just now. Please check your connection and try again.",
      "bot"
    );
  }
}

async function sendQuick(text) {
  const input = document.getElementById("chat-input");
  if (input) {
    input.value = "";
  }

  appendMessage(text, "user");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        user_id: currentUser ? currentUser.user_id : null,
      }),
    });

    if (!res.ok) {
      throw new Error("Server error " + res.status);
    }

    const data = await res.json();
    if (!data || data.success === false) {
      throw new Error(data && data.error ? data.error : "Unknown error");
    }

    appendMessage(data.reply, "bot");
    console.log("Chat intent:", data.intent, "mood:", data.mood);
  } catch (err) {
    console.error("Quick chat error:", err);
    appendMessage(
      "Hmm, something went wrong while sending that quick message. Please try again.",
      "bot"
    );
  }
}

function clearChat() {
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  appendMessage('Your local chat history has been cleared for this demo.', 'bot');
}

async function submitComplaint() {
  const nameInput = document.getElementById("complaint-name");
  const rollInput = document.getElementById("complaint-roll");
  const deptInput = document.getElementById("complaint-dept");
  const textInput = document.getElementById("complaint-text");
  const statusEl = document.getElementById("complaint-status");

  if (!nameInput || !rollInput || !deptInput || !textInput || !statusEl) return;

  const complaintText = textInput.value.trim();
  if (!complaintText) {
    statusEl.style.color = "#f87171";
    statusEl.textContent = "Please write your concern before submitting.";
    return;
  }

  statusEl.style.color = "#9ca3af";
  statusEl.textContent = "Sending...";

  try {
    const res = await fetch("/api/complaints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        studentname: nameInput.value.trim(),
        rollno: rollInput.value.trim(),
        department: deptInput.value.trim(),
        complainttext: complaintText,
      }),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to submit");
    }

    statusEl.style.color = "#22c55e";
    statusEl.textContent = "Thank you. Your concern has been submitted.";

    // Clear only the text; keep name/roll/department for repeat submissions if they want
    textInput.value = "";
  } catch (e) {
    console.error("Complaint submit error:", e);
    statusEl.style.color = "#f97316";
    statusEl.textContent = "Could not submit right now. Please try again later.";
  }
}

async function submitDeadline() {
  const labelInput = document.getElementById("deadline-label");
  const dateInput = document.getElementById("deadline-date");
  const typeSelect = document.getElementById("deadline-type");
  const courseInput = document.getElementById("deadline-course");
  const subjectInput = document.getElementById("deadline-subject");
  const statusEl = document.getElementById("deadline-status");

  if (!labelInput || !dateInput || !typeSelect || !statusEl) return;

  const label = labelInput.value.trim();
  const dueDate = dateInput.value; // browser gives YYYY-MM-DD
  if (!label || !dueDate) {
    statusEl.style.color = "#f87171";
    statusEl.textContent = "Please enter a title and due date.";
    return;
  }

  statusEl.style.color = "#9ca3af";
  statusEl.textContent = "Saving...";

  try {
    const res = await fetch("/api/deadlines", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        label,
        due_date: dueDate,
        type: typeSelect.value,
        course: courseInput.value.trim(),
        subject: subjectInput.value.trim(),
        visible_to: "student",
      }),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to save");
    }

    statusEl.style.color = "#22c55e";
    statusEl.textContent = "Deadline added.";

    // Clear minimal fields to allow quick repeated adds
    labelInput.value = "";
    dateInput.value = "";

    // Refresh student deadlines card
    if (typeof loadDeadlinesRightPanel === "function") {
      loadDeadlinesRightPanel();
    }
  } catch (e) {
    console.error("Add deadline error:", e);
    statusEl.style.color = "#f97316";
    statusEl.textContent = "Could not save right now. Please try again later.";
  }
}

// Keyboard UX for chat input: Enter = send, Shift+Enter = newline
document.addEventListener("DOMContentLoaded", () => {
  // Keyboard UX
  const input = document.getElementById("chat-input");
  if (input) {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        if (event.shiftKey) {
          return;
        }
        event.preventDefault();
        handleSend();
      }
    });
  }

  // Mobile sidebar toggle
  const mobileBtn = document.getElementById("mobile-menu-btn");
  const sidebar = document.querySelector(".sidebar");
  if (mobileBtn && sidebar) {
    mobileBtn.addEventListener("click", () => {
      sidebar.classList.toggle("sidebar-open");
    });
  }

  // Close sidebar when clicking a nav item on mobile
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      if (window.innerWidth <= 900) {
        const sb = document.querySelector(".sidebar");
        if (sb) sb.classList.remove("sidebar-open");
      }
    });
  });
});
