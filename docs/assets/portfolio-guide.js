(() => {
  const configs = {
    "enterprise-etl-platform": {
      index:"01 / 05", title:"Enterprise ETL Platform", version:"v0.5.0",
      role:"Enterprise Data Engineering Platform",
      focus:"ETL · Audit · Supply Chain · Observability",
      repo:"https://github.com/kewinall/enterprise-etl-platform",
      order:["interviewer","engineering-decisions","positioning","architecture","lifecycle","audit","supply","security","observe","quickstart","cicd","versions","repo","interview","demo"],
      nav:[["Fast Track","interviewer"],["Decisions","engineering-decisions"],["Positioning","positioning"],["Architecture","architecture"],["Core Flow","lifecycle"],["Governance","security"],["Observability","observe"],["Quick Start","quickstart"],["CI / Release","cicd"]]
    },
    "data-platform-mcp-server": {
      index:"02 / 05", title:"Data Platform MCP Server", version:"v0.4.0",
      role:"Tool / Integration Platform",
      focus:"MCP · Metadata · Lineage · Governed Access",
      repo:"https://github.com/kewinall/data-platform-mcp-server",
      order:["interviewer","engineering-decisions","architecture","flow","tools","lineage","security","tenant","observability","deploy","airgap","quickstart","cicd","versions","interview","faq","english"],
      nav:[["Fast Track","interviewer"],["Decisions","engineering-decisions"],["Architecture","architecture"],["Core Flow","flow"],["Capabilities","tools"],["Governance","security"],["Observability","observability"],["Quick Start","quickstart"],["CI / Release","cicd"]]
    },
    "agentic-dataops-copilot": {
      index:"03 / 05", title:"Agentic DataOps Copilot", version:"v0.5.0",
      role:"AI Reasoning / DataOps Operations",
      focus:"Triage · RCA · Policy · Human Approval",
      repo:"https://github.com/kewinall/agentic-dataops-copilot",
      order:["interview","engineering-decisions","position","architecture","agents","rag","mcp","governance","audit","scenario","quick","api","quality","evolution","qa","roadmap"],
      nav:[["Fast Track","interview"],["Decisions","engineering-decisions"],["Positioning","position"],["Architecture","architecture"],["Core Flow","agents"],["Governance","governance"],["Audit","audit"],["Quick Start","quick"],["CI / Release","quality"]]
    },
    "enterprise-rag-platform": {
      index:"04 / 05", title:"Enterprise RAG Platform", version:"v0.6.0",
      role:"Knowledge AI Platform",
      focus:"Hybrid RAG · Citation · Evaluation · Governance",
      repo:"https://github.com/kewinall/enterprise-rag-platform",
      order:["interview","engineering-decisions","role","architecture","rag","agent","features","security","evaluation","deploy","api","cicd","evolution","faq"],
      nav:[["Fast Track","interview"],["Decisions","engineering-decisions"],["Positioning","role"],["Architecture","architecture"],["Core Flow","rag"],["Governance","security"],["Evaluation","evaluation"],["Deploy","deploy"],["CI / Release","cicd"]]
    },
    "multi-llm-ai-gateway": {
      index:"05 / 05", title:"Multi-LLM AI Gateway", version:"v0.5.0",
      role:"Model Control Plane",
      focus:"Routing · Policy · Cost · Observability",
      repo:"https://github.com/kewinall/multi-llm-ai-gateway",
      order:["interview","engineering-decisions","positioning","architecture","request-flow","features","identity","policy","admin","observability","kubernetes","quickstart","api","cicd","versions","qa","limits"],
      nav:[["Fast Track","interview"],["Decisions","engineering-decisions"],["Positioning","positioning"],["Architecture","architecture"],["Core Flow","request-flow"],["Governance","policy"],["Observability","observability"],["Quick Start","quickstart"],["CI / Release","cicd"]]
    }
  };

  const slug = location.pathname.split("/").filter(Boolean)[0] || "";
  const cfg = configs[slug];
  if (!cfg) return;

  const init = () => {
    document.body.classList.add("pg-unified");
    applyStoredTheme();
    createTopbar(cfg);
    normalizeLayout(cfg);
    createSummary(cfg);
    reorderSections(cfg);
    decorateSections();
    createFooter(cfg);
  };

  function applyStoredTheme(){
    const saved = localStorage.getItem("kewinall-portfolio-theme") || "dark";
    document.documentElement.setAttribute("data-pg-theme", saved);
    document.documentElement.setAttribute("data-theme", saved);
  }

  function toggleTheme(){
    const current = document.documentElement.getAttribute("data-pg-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-pg-theme", next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("kewinall-portfolio-theme", next);
  }

  function createTopbar(cfg){
    document.getElementById("pgTopbar")?.remove();
    const header = document.createElement("header");
    header.id = "pgTopbar";
    const navLinks = cfg.nav
      .filter(([,id]) => document.getElementById(id))
      .map(([label,id]) => `<a href="#${id}">${label}</a>`)
      .join("");
    header.innerHTML = `
      <div class="pg-nav-inner">
        <a class="pg-brand" href="https://kewinall.github.io/kewinall/">
          <i class="pg-dot"></i>
          <span class="pg-title">${cfg.title}<small>Portfolio ${cfg.index} · ${cfg.role}</small></span>
        </a>
        <nav class="pg-links">${navLinks}</nav>
        <div class="pg-actions">
          <button id="pgThemeBtn" type="button">Theme</button>
          <a class="pg-action pg-hide-mobile" href="${cfg.repo}">GitHub</a>
          <a class="pg-action primary" href="https://kewinall.github.io/kewinall/">Portfolio</a>
        </div>
      </div>`;
    document.body.prepend(header);
    header.querySelector("#pgThemeBtn").addEventListener("click", toggleTheme);
  }

  function normalizeLayout(){
    const shell = document.querySelector(".shell");
    if (shell) shell.style.display = "block";
    const layout = document.querySelector(".layout");
    if (layout) layout.style.display = "block";
  }

  function findHero(){
    return document.querySelector("section.hero") ||
      document.querySelector("section#overview") ||
      document.querySelector("section#top") ||
      document.querySelector("section#cover");
  }

  function createSummary(cfg){
    document.querySelector(".pg-summary")?.remove();
    const summary = document.createElement("div");
    summary.className = "pg-summary";
    summary.innerHTML = `
      <div class="pg-summary-item"><span>Portfolio</span><strong>${cfg.index}</strong></div>
      <div class="pg-summary-item"><span>Primary Role</span><strong>${cfg.role}</strong></div>
      <div class="pg-summary-item"><span>Release</span><strong>${cfg.version}</strong></div>
      <div class="pg-summary-item"><span>Engineering Focus</span><strong>${cfg.focus}</strong></div>`;
    const hero = findHero();
    if (hero) hero.insertAdjacentElement("afterend", summary);
    else (document.querySelector("main") || document.body).prepend(summary);
  }

  function reorderSections(cfg){
    const all = [...document.querySelectorAll("section")];
    const hero = findHero();
    const sections = all.filter(s => s !== hero);
    if (!sections.length) return;

    const host = sections[0].closest("main") || document.querySelector("main") || sections[0].parentElement;
    let stack = document.getElementById("pgSectionStack");
    if (!stack){
      stack = document.createElement("div");
      stack.id = "pgSectionStack";
      host.insertBefore(stack, sections[0]);
    }

    const used = new Set();
    cfg.order.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.tagName.toLowerCase() === "section"){
        stack.appendChild(el);
        used.add(el);
      }
    });
    sections.filter(s => !used.has(s)).forEach(s => stack.appendChild(s));
  }

  function decorateSections(){
    const sections = [...document.querySelectorAll("#pgSectionStack > section")];
    sections.forEach((section, i) => {
      section.dataset.pgIndex = String(i + 1).padStart(2,"0");
    });
  }

  function createFooter(cfg){
    document.getElementById("pgFooter")?.remove();
    const footer = document.createElement("footer");
    footer.id = "pgFooter";
    footer.innerHTML = `
      <div><strong>${cfg.title}</strong><br>${cfg.role} · ${cfg.version}</div>
      <div>Production-oriented · Governed · Observable · Auditable</div>
      <div><a href="https://kewinall.github.io/kewinall/">Back to Portfolio</a> · <a href="${cfg.repo}">GitHub Repository</a></div>`;
    document.body.appendChild(footer);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();