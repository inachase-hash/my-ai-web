(function () {
  "use strict";

  var STORAGE_KEY = "ai-news-favorites";

  /* —— GitHub Contents API (favorites.json) —— */
  var GITHUB_OWNER = "inachase-hash";
  var GITHUB_REPO = "my-ai-web";
  var GITHUB_FILE_PATH = "favorites.json";
  var GITHUB_BRANCH = "main";
  var GITHUB_API = "https://api.github.com";
  /** Stored only in this browser — never committed (required for GitHub Pages). */
  var GITHUB_TOKEN_STORAGE_KEY = "ai-news-github-pat";

  /**
   * Token order: localStorage (from in-page form) → window.__GITHUB_FAVORITES_TOKEN__ (optional local file).
   * Do not commit tokens to the repo.
   */
  function getGithubToken() {
    if (typeof window === "undefined") return "";
    try {
      var fromLs = localStorage.getItem(GITHUB_TOKEN_STORAGE_KEY);
      if (fromLs && String(fromLs).trim()) return String(fromLs).trim();
    } catch (e) {}
    var t = window.__GITHUB_FAVORITES_TOKEN__;
    return t ? String(t).trim() : "";
  }

  function setGithubTokenInBrowser(token) {
    try {
      if (token && String(token).trim()) {
        localStorage.setItem(GITHUB_TOKEN_STORAGE_KEY, String(token).trim());
      } else {
        localStorage.removeItem(GITHUB_TOKEN_STORAGE_KEY);
      }
    } catch (e) {
      console.warn("[favorites] Could not store token:", e);
    }
  }

  function hasGithubTokenConfigured() {
    return !!getGithubToken();
  }

  function updateSyncPanelUi() {
    var hint = document.getElementById("github-token-status");
    if (!hint) return;
    if (hasGithubTokenConfigured()) {
      hint.textContent = "GitHub sync is on for this browser (token stored locally only).";
    } else {
      hint.textContent = "Add a token below to sync favorites.json to your repo from any device.";
    }
  }

  function githubContentsApiUrl() {
    return (
      GITHUB_API +
      "/repos/" +
      encodeURIComponent(GITHUB_OWNER) +
      "/" +
      encodeURIComponent(GITHUB_REPO) +
      "/contents/" +
      encodeURIComponent(GITHUB_FILE_PATH)
    );
  }

  function githubHeaders(token) {
    return {
      Accept: "application/vnd.github+json",
      Authorization: "Bearer " + token,
      "X-GitHub-Api-Version": "2022-11-28",
    };
  }

  function toBase64Utf8(str) {
    return btoa(unescape(encodeURIComponent(str)));
  }

  function decodeBase64Utf8(b64) {
    var cleaned = String(b64).replace(/\s/g, "");
    var binary = atob(cleaned);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new TextDecoder("utf-8").decode(bytes);
  }

  function normalizeFavoriteItem(item) {
    if (!item || typeof item.link !== "string" || !item.link) return null;
    return {
      title: String(item.title || ""),
      link: item.link,
      source: String(item.source || ""),
      saved_at: String(item.saved_at || ""),
    };
  }

  function normalizeFavoriteList(arr) {
    if (!Array.isArray(arr)) return [];
    var seen = new Set();
    var out = [];
    for (var i = 0; i < arr.length; i++) {
      var n = normalizeFavoriteItem(arr[i]);
      if (!n || seen.has(n.link)) continue;
      seen.add(n.link);
      out.push(n);
    }
    return out;
  }

  /**
   * Merge by link. Newer saved_at wins; on tie, the later list wins (local is merged after remote).
   */
  function mergeFavoriteLists(local, remote) {
    var map = Object.create(null);
    function upsert(item) {
      var n = normalizeFavoriteItem(item);
      if (!n) return;
      var k = n.link;
      var cur = map[k];
      if (!cur) {
        map[k] = n;
        return;
      }
      var nt = n.saved_at || "";
      var ct = cur.saved_at || "";
      if (nt > ct || nt === ct) map[k] = n;
    }
    for (var i = 0; i < remote.length; i++) upsert(remote[i]);
    for (var j = 0; j < local.length; j++) upsert(local[j]);
    var out = [];
    for (var link in map) {
      if (Object.prototype.hasOwnProperty.call(map, link)) out.push(map[link]);
    }
    out.sort(function (a, b) {
      return (b.saved_at || "").localeCompare(a.saved_at || "");
    });
    return normalizeFavoriteList(out);
  }

  function favoritesStableJson(arr) {
    var copy = arr.slice().sort(function (a, b) {
      return a.link.localeCompare(b.link);
    });
    return JSON.stringify(copy);
  }

  function setSyncStatus(text) {
    var el = document.getElementById("github-sync-status");
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = text;
  }

  /**
   * GET remote file. Returns { list, sha } or null on any failure (caller uses local only).
   * 404 → empty list, sha null (create on first PUT).
   */
  function loadFavoritesFromGithub() {
    return new Promise(function (resolve) {
      var token = getGithubToken();
      if (!token) {
        resolve(null);
        return;
      }
      var url =
        githubContentsApiUrl() + "?ref=" + encodeURIComponent(GITHUB_BRANCH);
      fetch(url, { headers: githubHeaders(token) })
        .then(function (res) {
          if (res.status === 404) {
            resolve({ list: [], sha: null });
            return;
          }
          if (!res.ok) {
            return res.text().then(function (txt) {
              console.warn("[favorites] GitHub GET failed:", res.status, txt);
              resolve(null);
            });
          }
          return res.json().then(function (data) {
            if (!data || typeof data.content !== "string") {
              resolve({ list: [], sha: data && data.sha ? data.sha : null });
              return;
            }
            var jsonStr = decodeBase64Utf8(data.content);
            var parsed;
            try {
              parsed = JSON.parse(jsonStr);
            } catch (e) {
              console.warn("[favorites] Invalid JSON in favorites.json on GitHub");
              resolve(null);
              return;
            }
            resolve({
              list: normalizeFavoriteList(parsed),
              sha: data.sha || null,
            });
          });
        })
        .catch(function (err) {
          console.warn("[favorites] GitHub GET error:", err);
          resolve(null);
        });
    });
  }

  /** Save current localStorage favorites to GitHub (read sha, then PUT). Never throws. */
  function saveFavoritesToGithub() {
    return new Promise(function (resolve) {
      var token = getGithubToken();
      if (!token) {
        resolve(false);
        return;
      }
      var list = normalizeFavoriteList(loadFavorites());
      var body = JSON.stringify(list, null, 2);
      var contentB64 = toBase64Utf8(body);

      loadFavoritesFromGithub()
        .then(function (remote) {
          if (remote === null) {
            setSyncStatus("Cloud unavailable — using this device only");
            resolve(false);
            return;
          }
          var payload = {
            message: "chore: sync favorites (AI News)",
            content: contentB64,
            branch: GITHUB_BRANCH,
          };
          if (remote.sha) payload.sha = remote.sha;

          return fetch(githubContentsApiUrl(), {
            method: "PUT",
            headers: Object.assign(
              { "Content-Type": "application/json" },
              githubHeaders(token)
            ),
            body: JSON.stringify(payload),
          }).then(function (res) {
            if (!res.ok) {
              return res.text().then(function (txt) {
                console.warn("[favorites] GitHub PUT failed:", res.status, txt);
                setSyncStatus("Could not save to GitHub — kept on this device");
                resolve(false);
              });
            }
            setSyncStatus("Synced with GitHub");
            resolve(true);
          });
        })
        .catch(function (err) {
          console.warn("[favorites] GitHub PUT error:", err);
          setSyncStatus("Could not save to GitHub — kept on this device");
          resolve(false);
        });
    });
  }

  var pushTimer = null;
  function scheduleGithubPush() {
    if (!getGithubToken()) return;
    if (pushTimer) clearTimeout(pushTimer);
    pushTimer = setTimeout(function () {
      pushTimer = null;
      saveFavoritesToGithub();
    }, 800);
  }

  /** Pull from GitHub, merge into localStorage, refresh UI; then push merged snapshot. */
  function syncFromGithubOnLoad() {
    if (!getGithubToken()) return;
    setSyncStatus("Syncing with GitHub…");
    loadFavoritesFromGithub()
      .then(function (remote) {
        if (remote === null) {
          setSyncStatus("Cloud unavailable — using this device only");
          return;
        }
        var local = normalizeFavoriteList(loadFavorites());
        var merged = mergeFavoriteLists(local, remote.list);
        var before = favoritesStableJson(local);
        var after = favoritesStableJson(merged);
        if (before !== after) {
          saveFavorites(merged);
          syncFeedStars();
          renderFavorites();
          return saveFavoritesToGithub();
        }
        setSyncStatus("Synced with GitHub");
      })
      .catch(function (err) {
        console.warn("[favorites] syncFromGithubOnLoad:", err);
        setSyncStatus("Cloud unavailable — using this device only");
      });
  }

  /* —— localStorage (unchanged behavior) —— */

  function loadFavorites() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var data = JSON.parse(raw);
      return normalizeFavoriteList(data);
    } catch (e) {
      return [];
    }
  }

  function saveFavorites(list) {
    var deduped = normalizeFavoriteList(list);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(deduped));
  }

  function isFavorited(link) {
    if (!link) return false;
    var favs = loadFavorites();
    for (var i = 0; i < favs.length; i++) {
      if (favs[i].link === link) return true;
    }
    return false;
  }

  function findFeedCardByLink(link) {
    var feed = document.getElementById("feed");
    if (!feed) return null;
    var cards = feed.querySelectorAll("article.card");
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].dataset.link === link) return cards[i];
    }
    return null;
  }

  function setStarButtonState(btn, on) {
    if (!btn) return;
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.setAttribute("aria-label", on ? "Remove from favorites" : "Add to favorites");
    btn.textContent = on ? "\u2b50" : "\u2606";
  }

  function syncFeedStars() {
    var favs = loadFavorites();
    var set = new Set();
    for (var i = 0; i < favs.length; i++) set.add(favs[i].link);

    var feed = document.getElementById("feed");
    if (!feed) return;
    var cards = feed.querySelectorAll("article.card");
    for (var j = 0; j < cards.length; j++) {
      var card = cards[j];
      var link = card.dataset.link;
      var on = link && set.has(link);
      card.classList.toggle("is-favorited", !!on);
      setStarButtonState(card.querySelector(".star-btn"), !!on);
    }
  }

  function formatSavedAt(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return d.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch (e) {
      return iso;
    }
  }

  function renderFavorites() {
    var listEl = document.getElementById("favorites-list");
    var emptyEl = document.getElementById("favorites-empty");
    if (!listEl) return;

    var items = loadFavorites();
    if (emptyEl) emptyEl.hidden = items.length > 0;

    listEl.replaceChildren();

    for (var i = 0; i < items.length; i++) {
      var f = items[i];
      var article = document.createElement("article");
      article.className = "card card-favorite is-favorited";
      article.dataset.link = f.link;
      article.dataset.title = f.title;
      article.dataset.source = f.source;

      var inner = document.createElement("div");
      inner.className = "card-inner";

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "star-btn";
      setStarButtonState(btn, true);

      var content = document.createElement("div");
      content.className = "card-content";

      var h2 = document.createElement("h2");
      h2.className = "title";
      var a = document.createElement("a");
      a.href = f.link;
      a.rel = "noopener noreferrer";
      a.target = "_blank";
      a.textContent = f.title || f.link;
      h2.appendChild(a);

      var meta = document.createElement("p");
      meta.className = "meta";
      var sourceSpan = document.createElement("span");
      sourceSpan.className = "source";
      sourceSpan.textContent = f.source || "\u2014";
      meta.appendChild(sourceSpan);

      if (f.saved_at) {
        var saved = document.createElement("span");
        saved.className = "saved-at";
        saved.textContent = "Saved " + formatSavedAt(f.saved_at);
        meta.appendChild(saved);
      }

      content.appendChild(h2);
      content.appendChild(meta);
      inner.appendChild(btn);
      inner.appendChild(content);
      article.appendChild(inner);
      listEl.appendChild(article);
    }
  }

  function toggleFavorite(link) {
    if (!link) return;
    var favs = loadFavorites();
    var idx = -1;
    for (var i = 0; i < favs.length; i++) {
      if (favs[i].link === link) {
        idx = i;
        break;
      }
    }

    if (idx >= 0) {
      favs.splice(idx, 1);
      saveFavorites(favs);
      syncFeedStars();
      renderFavorites();
      scheduleGithubPush();
      return;
    }

    var feedCard = findFeedCardByLink(link);
    var title = feedCard && feedCard.dataset.title ? feedCard.dataset.title : "";
    var source = feedCard && feedCard.dataset.source ? feedCard.dataset.source : "";

    favs.push({
      title: title,
      link: link,
      source: source,
      saved_at: new Date().toISOString(),
    });
    saveFavorites(favs);
    syncFeedStars();
    renderFavorites();
    scheduleGithubPush();
  }

  function onStarClick(event) {
    var btn = event.target.closest(".star-btn");
    if (!btn) return;
    var article = btn.closest("article.card");
    if (!article || !article.dataset.link) return;
    event.preventDefault();
    toggleFavorite(article.dataset.link);
  }

  function wireGithubSyncPanel() {
    var input = document.getElementById("github-token-input");
    var saveBtn = document.getElementById("github-token-save");
    var clearBtn = document.getElementById("github-token-clear");
    if (saveBtn) {
      saveBtn.addEventListener("click", function () {
        var v = input && input.value ? input.value.trim() : "";
        if (!v) {
          setSyncStatus("Paste a GitHub token first.");
          return;
        }
        setGithubTokenInBrowser(v);
        if (input) input.value = "";
        updateSyncPanelUi();
        syncFromGithubOnLoad();
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        setGithubTokenInBrowser("");
        if (input) input.value = "";
        updateSyncPanelUi();
        setSyncStatus("");
      });
    }
    updateSyncPanelUi();
  }

  document.addEventListener("DOMContentLoaded", function () {
    syncFeedStars();
    renderFavorites();
    document.body.addEventListener("click", onStarClick);
    wireGithubSyncPanel();
    syncFromGithubOnLoad();
  });

  window.loadFavorites = loadFavorites;
  window.saveFavorites = saveFavorites;
  window.toggleFavorite = toggleFavorite;
  window.isFavorited = isFavorited;
  window.renderFavorites = renderFavorites;
})();
