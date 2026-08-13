(function () {
  if (window.__tivoliSolariInjected) {
    return;
  }
  window.__tivoliSolariInjected = true;

  function addButton() {
    if (document.getElementById("tivoli-solari-btn")) {
      return;
    }
    var btn = document.createElement("button");
    btn.id = "tivoli-solari-btn";
    btn.type = "button";
    btn.textContent = "SOLARI";
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      fetch("http://127.0.0.1:4011/solari", { method: "GET", mode: "cors" }).catch(function () {});
    }, true);
    (document.body || document.documentElement).appendChild(btn);
  }

  function hideGeniusError() {
    var needle = "Genius Access Token";
    var nodes = document.querySelectorAll("div, span, p, h1, h2, h3, section, article");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var text = el.textContent || "";
      if (text.indexOf(needle) === -1 && text.indexOf("Token missing") === -1) {
        continue;
      }
      if (text.length > 280) {
        continue;
      }
      var box = el;
      for (var d = 0; d < 5 && box && box !== document.body; d++) {
        if (box.childElementCount > 8) {
          break;
        }
        box = box.parentElement;
      }
      if (box && box !== document.body) {
        box.style.display = "none";
      }
    }
  }

  function tick() {
    addButton();
    hideGeniusError();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tick);
  } else {
    tick();
  }
  setInterval(tick, 1500);
})();
