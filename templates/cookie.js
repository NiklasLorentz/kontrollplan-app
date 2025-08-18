
(function(){
  const CONSENT_KEY = "cookieConsent"; // "accepted" | "declined"
  const GA_ID = "{{ GA_ID|default('') }}";
  const MATOMO_URL = "{{ MATOMO_URL|default('') }}";
  const MATOMO_SITE_ID = "{{ MATOMO_SITE_ID|default('') }}";

  function showBanner(){ const el=document.getElementById('cookie-banner'); if(el) el.hidden=false; }
  function hideBanner(){ const el=document.getElementById('cookie-banner'); if(el) el.hidden=true; }

  function loadGA(id){
    if(!id) return;
    const s1=document.createElement('script');
    s1.async=true; s1.src=`https://www.googletagmanager.com/gtag/js?id=${id}`;
    document.head.appendChild(s1);
    const s2=document.createElement('script');
    s2.innerHTML=`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${id}',{ anonymize_ip:true });`;
    document.head.appendChild(s2);
  }

  function loadMatomo(url, siteId){
    if(!url || !siteId) return;
    const s=document.createElement('script');
    s.innerHTML=`var _paq=window._paq=window._paq||[];_paq.push(['trackPageView']);_paq.push(['enableLinkTracking']);(function(){var u='${"{{MATOMO_URL}}"}'.replace(/\/+$/,'/') ;_paq.push(['setTrackerUrl', u+'matomo.php']);_paq.push(['setSiteId','${siteId}']);var d=document,g=d.createElement('script'),s=d.getElementsByTagName('script')[0];g.async=true;g.src=u+'matomo.js';s.parentNode.insertBefore(g,s);})();`;
    document.head.appendChild(s);
  }

  function initAnalytics(){ loadGA(GA_ID); loadMatomo(MATOMO_URL, MATOMO_SITE_ID); }

  function init(){
    const state=localStorage.getItem(CONSENT_KEY);
    if(state==='accepted'){ initAnalytics(); hideBanner(); return; }
    if(state==='declined'){ hideBanner(); return; }
    showBanner();
    const accept=document.getElementById('cookie-accept');
    const decline=document.getElementById('cookie-decline');
    accept && (accept.onclick=function(){ localStorage.setItem(CONSENT_KEY,'accepted'); initAnalytics(); hideBanner(); });
    decline && (decline.onclick=function(){ localStorage.setItem(CONSENT_KEY,'declined'); hideBanner(); });
  }

  document.addEventListener('DOMContentLoaded', init);

  window.resetCookies = function(){
    localStorage.removeItem('cookieConsent');
    showBanner();
  }
})();
