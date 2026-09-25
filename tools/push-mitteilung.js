// Schickt eine Push-Mitteilung zur letzten Änderung an alle Geräte aus dem Secret PUSH_SUBSCRIPTIONS.
// Läuft in der GitHub Action .github/workflows/mitteilung.yml.
const { execSync } = require("child_process");
const fs = require("fs");
const webpush = require("web-push");

// Muss zum Schlüssel VAPID_PUBLIC in index.html passen
const VAPID_PUBLIC = "BFMgiDxvOr-9Ti39Z3UD7T3D2L5xq4qsTCJVNuWhDL8xBhspeywhwyYdWv6Dgx7fd-JvOjOzn2WpzusALIV5zsc";
const SITE = "https://thomasskornia-source.github.io/Gravel-Kompass/";

const { VAPID_PRIVATE_KEY, PUSH_SUBSCRIPTIONS = "", EVENT, BEFORE = "", COMMIT_MSG = "" } = process.env;
if (!VAPID_PRIVATE_KEY || !PUSH_SUBSCRIPTIONS.trim()) {
  console.log("Secrets VAPID_PRIVATE_KEY/PUSH_SUBSCRIPTIONS fehlen – keine Mitteilung.");
  process.exit(0);
}

// Secret: ein Abo-Objekt, eine Liste davon oder mehrere Objekte je Zeile
function parseSubs(text) {
  text = text.trim();
  try { const v = JSON.parse(text); return Array.isArray(v) ? v : [v]; } catch (e) {}
  return text.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => JSON.parse(l));
}

function sh(cmd) { return execSync(cmd, { encoding: "utf8" }).trim(); }

function message() {
  if (EVENT !== "push") return { title: "Gravel Kompass", body: "Test-Mitteilung – Mitteilungen funktionieren ✓", url: "./" };
  const subject = COMMIT_MSG.split("\n")[0] || "Neue Änderung";
  const base = /^0+$/.test(BEFORE) || !BEFORE ? "HEAD~1" : BEFORE;
  let changed = [];
  try { changed = sh(`git diff --name-status ${base} HEAD -- data/tours`).split("\n").filter(Boolean); } catch (e) {}
  const tours = changed.map((l) => l.split("\t")).filter(([, f]) => /^data\/tours\/[^/]+\.json$/.test(f || ""));
  if (tours.length === 1) {
    const [status, file] = tours[0];
    const id = file.replace(/^data\/tours\/|\.json$/g, "");
    let title = id;
    try { title = JSON.parse(fs.readFileSync(file, "utf8")).title || id; } catch (e) {}
    return { title: (status === "A" ? "🚴 Neue Tour: " : "✏️ Tour geändert: ") + title, body: subject, url: "./#tour/" + id };
  }
  return { title: "Gravel Kompass", body: subject, url: "./" };
}

(async () => {
  webpush.setVapidDetails(SITE, VAPID_PUBLIC, VAPID_PRIVATE_KEY);
  const payload = message();
  console.log("Mitteilung:", payload);
  let ok = 0;
  for (const sub of parseSubs(PUSH_SUBSCRIPTIONS)) {
    try {
      await webpush.sendNotification(sub, JSON.stringify(payload), { TTL: 86400 });
      ok++;
    } catch (e) {
      const hint = e.statusCode === 404 || e.statusCode === 410 ? " (Abo abgelaufen – in der App neu aktivieren und Secret ersetzen)" : "";
      console.log(`Fehler ${e.statusCode || e.message} bei ${String(sub.endpoint).slice(0, 40)}…${hint}`);
    }
  }
  console.log(`${ok} Mitteilung(en) verschickt.`);
})();
