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
 *     Außerdem Eigenschaft ZUGANGSCODE mit dem Code anlegen, den Thomas an Freunde weitergibt
 *     (Sperre gegen Spam; ohne diese Eigenschaft wird jeder Eintrag gesperrt).
 *  2. Oben die Funktion `einrichten` auswählen → Ausführen → Berechtigungen erlauben.
 *  3. Zum Prüfen `testAusloesen` ausführen – in claude.ai/code muss ein neuer Lauf erscheinen.
 */

var ROUTINE_URL = 'https://api.anthropic.com/v1/claude_code/routines/trig_013pxFNYhiQ5oL5i45RhFXk2/fire';

// Header wie im Beispiel-Aufruf (curl) des API-Auslösers – bei Abweichung dort übernehmen.
var ANTHROPIC_VERSION = '2023-06-01';
var ANTHROPIC_BETA = 'experimental-cc-routine-2026-04-01';

/** Legt den Auslöser „bei Formularübermittlung“ an (vorhandene werden vorher entfernt). */
// Tabelle „Gravel Kompass Eingang“ – damit das Skript auch als eigenständiges Projekt funktioniert
// (ohne Zugriffsrecht auf die Tabelle nützt die ID niemandem)
var TABELLE_ID = '16S3URnGUKnyW1T2-j_kHa5K50CnNeCNA77q8X9npotw';

function einrichten() {
  var ss = SpreadsheetApp.getActive() || SpreadsheetApp.openById(TABELLE_ID);
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'beiNeuerAntwort') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('beiNeuerAntwort').forSpreadsheet(ss).onFormSubmit().create();
  Logger.log('Auslöser eingerichtet.');
}

// Sperre gegen Spam: höchstens so viele Routine-Läufe pro Tag
var MAX_LAEUFE_PRO_TAG = 20;

/** Wird bei jeder neuen Formular-Antwort aufgerufen. */
function beiNeuerAntwort(e) {
  var werte = (e && e.namedValues) || {};
  var typ = String((werte['Typ'] || [''])[0]).trim();
  var zeit = String((werte['Zeitstempel'] || [''])[0]).trim();
  if (typ === 'Test') return; // Testeinträge lösen keinen Lauf aus

  // Zugangscode prüfen, aus der Nachricht entfernen und Ergebnis in Spalte „Freigabe“ vermerken
  var freigabe = zugangPruefen(e);
  if (freigabe !== 'ok') {
    Logger.log('Eintrag vom ' + zeit + ' gesperrt: ' + freigabe);
    return;
  }
  if (!tageslimitOk()) {
    Logger.log('Tageslimit erreicht – Eintrag vom ' + zeit + ' wird beim nächsten Lauf erledigt.');
    return;
  }
  routineStarten('Neuer Eintrag im Eingang: ' + (typ || 'unbekannt') + ' vom ' + zeit + '.');
}

/** Liefert 'ok' oder den Sperrgrund und schreibt ihn in die Spalte „Freigabe“ der Zeile. */
function zugangPruefen(e) {
  var blatt = e.range.getSheet();
  var zeile = e.range.getRow();
  var kopf = blatt.getRange(1, 1, 1, blatt.getLastColumn()).getValues()[0].map(String);
  var spNachricht = kopf.indexOf('Nachricht') + 1;
  var spFreigabe = kopf.indexOf('Freigabe') + 1;
  if (!spFreigabe) {
    spFreigabe = kopf.length + 1;
    blatt.getRange(1, spFreigabe).setValue('Freigabe');
  }

  var nachricht = spNachricht ? String(blatt.getRange(zeile, spNachricht).getValue()) : '';
  var treffer = nachricht.match(/\s*Zugangscode:[ \t]*(.*)\s*$/);
  var eingegeben = treffer ? treffer[1].trim() : '';
  if (treffer && spNachricht) {
    // Code nicht in der Tabelle stehen lassen (die Routine und das Repo sollen ihn nie sehen)
    blatt.getRange(zeile, spNachricht).setValue(nachricht.slice(0, treffer.index));
  }

  var erwartet = String(PropertiesService.getScriptProperties().getProperty('ZUGANGSCODE') || '').trim();
  var ergebnis;
  if (!erwartet) ergebnis = 'gesperrt: ZUGANGSCODE nicht eingerichtet';
  else if (!eingegeben) ergebnis = 'gesperrt: kein Zugangscode';
  else if (eingegeben.toLowerCase() !== erwartet.toLowerCase()) ergebnis = 'gesperrt: falscher Zugangscode';
  else ergebnis = 'ok';
  blatt.getRange(zeile, spFreigabe).setValue(ergebnis);
  return ergebnis;
}

/** Zählt die Läufe pro Tag; false, wenn das Tageslimit erreicht ist. */
function tageslimitOk() {
  var props = PropertiesService.getScriptProperties();
  var heute = Utilities.formatDate(new Date(), 'Europe/Berlin', 'yyyy-MM-dd');
  var zaehler = JSON.parse(props.getProperty('LAEUFE') || '{}');
  var n = zaehler[heute] || 0;
  if (n >= MAX_LAEUFE_PRO_TAG) return false;
  var neu = {};
  neu[heute] = n + 1;
  props.setProperty('LAEUFE', JSON.stringify(neu));
  return true;
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
  var text = antwort.getContentText();
  Logger.log('Routine: HTTP ' + code + ' ' + text);
  if (code >= 200 && code < 300) {
    cache.put('laeuft', '1', 120);
  } else if (code === 400 || code === 409 || code === 429) {
    // Meist läuft die Routine gerade noch (sie nimmt neue Einträge dann evtl. nicht mehr mit):
    // kein Fehler-Mail, sondern in 10 Minuten einmal erneut starten.
    Logger.log('Routine gerade nicht startbar – neuer Versuch in 10 Minuten.');
    nachholenPlanen();
  } else {
    throw new Error('Routine nicht gestartet: HTTP ' + code + ' ' + text.slice(0, 300));
  }
}

/** Plant einen einmaligen Nachhol-Start (höchstens einer gleichzeitig). */
function nachholenPlanen() {
  var geplant = ScriptApp.getProjectTriggers().some(function (t) { return t.getHandlerFunction() === 'nachholen'; });
  if (!geplant) ScriptApp.newTrigger('nachholen').timeBased().after(10 * 60 * 1000).create();
}

/** Wird vom Nachhol-Auslöser aufgerufen; entfernt sich selbst und startet die Routine erneut. */
function nachholen() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'nachholen') ScriptApp.deleteTrigger(t);
  });
  CacheService.getScriptCache().remove('laeuft');
  routineStarten('Nachhol-Start: Eintrag kam, während die Routine noch lief.');
}
