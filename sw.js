// Gravel Kompass service worker: push notifications and the red badge on the home-screen icon
var BADGE_CACHE = "gk-badge";

function getCount(){
  return caches.open(BADGE_CACHE).then(function(c){ return c.match("count"); })
    .then(function(r){ return r ? r.text() : "0"; })
    .then(function(t){ return parseInt(t, 10) || 0; })
    .catch(function(){ return 0; });
}
function setCount(n){
  return caches.open(BADGE_CACHE).then(function(c){ return c.put("count", new Response(String(n))); });
}

self.addEventListener("install", function(){ self.skipWaiting(); });
self.addEventListener("activate", function(e){ e.waitUntil(self.clients.claim()); });

self.addEventListener("push", function(e){
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = {body: e.data ? e.data.text() : ""}; }
  e.waitUntil(getCount().then(function(n){
    n += 1;
    return setCount(n).then(function(){
      if (self.navigator.setAppBadge) return self.navigator.setAppBadge(n).catch(function(){});
    });
  }).then(function(){
    return self.registration.showNotification(d.title || "Gravel Kompass", {
      body: d.body || "",
      icon: "icons/icon-192.png",
      data: {url: d.url || "./"}
    });
  }));
});

self.addEventListener("notificationclick", function(e){
  e.notification.close();
  var url = new URL(e.notification.data && e.notification.data.url || "./", self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(function(list){
    for (var i = 0; i < list.length; i++){
      if ("focus" in list[i]) return list[i].navigate(url).then(function(c){ return c && c.focus(); });
    }
    return self.clients.openWindow(url);
  }));
});
