// Compatibility redirect: all hour calculation and display uses the shared HR view.
location.replace('hr.html?view=hours&legacy_username='+encodeURIComponent(new URLSearchParams(location.search).get('username')||''));
