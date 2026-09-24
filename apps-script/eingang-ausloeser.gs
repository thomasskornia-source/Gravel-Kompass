/**
 * Gravel Kompass – Eingang sofort abarbeiten lassen.
 *
 * Gehört in die Google-Tabelle „Gravel Kompass Eingang“ (Erweiterungen → Apps Script).
 * Bei jeder neuen Formular-Antwort wird die Claude-Routine „Gravel Kompass täglich abarbeiten“
 * über ihren API-Auslöser gestartet. Die Routine liest dann die Tabelle und arbeitet alle
 * offenen Einträge nach ABLAUF.md ab.
 *
 * Einrichten (einmalig):
 *  1. Projekteinstellungen (Zahnrad) → Skripteigenschaften → Eigenschaft ROUTINE_TOKEN
 *     mit dem Schlüssel des API-Auslösers anlegen. Der Schlüssel steht NICHT im Code.
 *  2. Oben die Funktion `einrichten` auswählen → Ausführen → Berechtigungen erlauben.
 *  3. Zum Prüfen `testAusloesen` ausführen – in claude.ai/code muss ein neuer Lauf erscheinen.
 */

var ROUTINE_URL = 'https://api.anthropic.com/v1/claude_code/routines/trig_013pxFNYhiQ5oL5i45RhFXk2/fire';

// Header wie im Beispiel-Aufruf (curl) des API-Auslösers – bei Abweichung dort übernehmen.
var ANTHROPIC_VERSION = '2023-06-01';
var ANTHROPIC_BETA = 'experimental-cc-routine-2026-04-01';

/** Legt den Auslöser „bei Formularübermittlung“ an (vorhandene werden vorher entfernt). */
function einrichten() {
  var ss = SpreadsheetApp.getActive();
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'beiNeuerAntwort') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('beiNeuerAntwort').forSpreadsheet(ss).onFormSubmit().create();
  Logger.log('Auslöser eingerichtet.');
}

/** Wird bei jeder neuen Formular-Antwort aufgerufen. */
function beiNeuerAntwort(e) {
  var werte = (e && e.namedValues) || {};
  var typ = String((werte['Typ'] || [''])[0]).trim();
  var zeit = String((werte['Zeitstempel'] || [''])[0]).trim();
  if (typ === 'Test') return; // Testeinträge lösen keinen Lauf aus
  routineStarten('Neuer Eintrag im Eingang: ' + (typ || 'unbekannt') + ' vom ' + zeit + '.');
}

/** Manuell ausführen, um die Verbindung zu prüfen. */
function testAusloesen() {
  routineStarten('Testaufruf aus Apps Script.');
}

function routineStarten(hinweis) {
  var token = PropertiesService.getScriptProperties().getProperty('ROUTINE_TOKEN');
  if (!token) throw new Error('Skripteigenschaft ROUTINE_TOKEN fehlt.');
  // Mehrere Antworten kurz hintereinander: höchstens ein Lauf pro 2 Minuten,
  // die Routine arbeitet ohnehin alle offenen Einträge ab.
  var cache = CacheService.getScriptCache();
  if (cache.get('laeuft')) return;
  var antwort = UrlFetchApp.fetch(ROUTINE_URL, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + token,
      'anthropic-version': ANTHROPIC_VERSION,
      'anthropic-beta': ANTHROPIC_BETA
    },
    payload: JSON.stringify({ text: hinweis }),
    muteHttpExceptions: true
  });
  var code = antwort.getResponseCode();
  Logger.log('Routine: HTTP ' + code + ' ' + antwort.getContentText());
  if (code >= 200 && code < 300) {
    cache.put('laeuft', '1', 120);
  } else {
    throw new Error('Routine nicht gestartet: HTTP ' + code);
  }
}
