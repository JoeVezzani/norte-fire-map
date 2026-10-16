/* icons.js : wildfire evacuation map icon family.
   24x24 grid, 2px round strokes, currentColor main color, white halo underneath.
   Tokens inside glyphs: {c} = main color, {k} = knockout color (white on panel, badge color in markers). */
(function () {
  var P = {
    red: '#e5484d', orange: '#f76b15', amber: '#f5b400', green: '#1f8a4c', blue: '#2f6feb',
    purple: '#6d28d9', slate: '#7c8a99', ink: '#0b0d10', white: '#ffffff'
  };

  var G = {
    // ORDER: filled house, knocked-out door, exit arrow leaving it (go now)
    order: '<path d="M2 11l6.5-6 6.5 6v9H2z" fill="{c}"/>' +
      '<path d="M6.5 20v-4.5h4V20z" fill="{k}" stroke="none"/>' +
      '<path d="M17.5 13H22M19.5 10.5L22 13l-2.5 2.5"/>',
    // WARNING: filled house with knocked-out exclamation (be ready)
    warning: '<path d="M3 11l9-8 9 8v10H3z" fill="{c}"/>' +
      '<path d="M12 9.5v4.5" stroke="{k}" stroke-width="2.4"/>' +
      '<circle cx="12" cy="17.3" r="1.3" fill="{k}" stroke="none"/>',
    // SHELTER: tent with knocked-out doorway
    shelter: '<path d="M12 3L2.5 20.5h19z" fill="{c}"/>' +
      '<path d="M12 12.5l-3.8 8h7.6z" fill="{k}" stroke="none"/>',
    // SCHOOL: mortarboard
    school: '<path d="M2 9.5L12 4.5l10 5-10 5z" fill="{c}"/>' +
      '<path d="M6 11.8V16c0 1.6 2.7 3 6 3s6-1.4 6-3v-4.2M22 9.5V15"/>',
    // WIND: arrow pointing UP, symmetric about (12,12) so CSS rotate() stays centered
    wind: '<path d="M12 3l6.5 8H14v10h-4V11H5.5z" fill="{c}"/>',
    // PHOTO: camera body with knocked-out lens
    photo: '<path d="M8 7l1.6-2.5h4.8L16 7"/>' +
      '<rect x="2" y="7" width="20" height="13" rx="3" fill="{c}"/>' +
      '<circle cx="12" cy="13.5" r="3.4" stroke="{k}"/>',
    // VIDEO: camcorder
    video: '<rect x="2" y="6" width="13.5" height="12" rx="3" fill="{c}"/>' +
      '<path d="M15.5 10.5L22 7v10l-6.5-3.5z" fill="{c}"/>',
    // POST: speech bubble (count text appended by ICONS.post(n))
    post: '<path d="M5 3h14a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-6l-5 4v-4H5a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3z" fill="{c}"/>',
    // ORIGIN: flame with knocked-out inner flame
    origin: '<path d="M12 2c1 4 6.5 6 6.5 12a6.5 6.5 0 0 1-13 0c0-3.2 2-5.2 3-7.2 1 2 2 3 3 3-1-3-.3-5.8.5-7.8z" fill="{c}"/>' +
      '<path d="M12 20.2a2.6 2.6 0 0 1-2.6-2.6c0-1.6 1.5-2.6 2.6-4.2 1.1 1.6 2.6 2.6 2.6 4.2a2.6 2.6 0 0 1-2.6 2.6z" fill="{k}" stroke="none"/>',
    // FRONT: active head point, ring around a small solid flame
    front: '<circle cx="12" cy="12" r="9"/>' +
      '<path d="M12 6.5c.6 2.3 3.8 3.5 3.8 6.8a3.8 3.8 0 0 1-7.6 0c0-1.8 1.1-2.9 1.7-4 .6 1.1 1.1 1.7 1.7 1.7-.5-1.7 0-3.4.4-4.5z" fill="{c}"/>',
    // CLOSURE: road barricade, knocked-out hazard stripes
    closure: '<path d="M6 14.5V21M18 14.5V21M6 7.5V4.5M18 7.5V4.5"/>' +
      '<rect x="2" y="7.5" width="20" height="7" rx="1.5" fill="{c}"/>' +
      '<path d="M8 8.5l-3 5M13.5 8.5l-3 5M19 8.5l-3 5" stroke="{k}" stroke-width="1.8"/>',
    // LANDFILL / LANDMARK: flagged mound
    landfill: '<path d="M3 20.5c2-4.5 5-7 9-7s7 2.5 9 7z" fill="{c}"/>' +
      '<path d="M12 13.5V3.5"/><path d="M12 3.5l6 2.6-6 2.6z" fill="{c}"/>',
    // HOSPITAL: rounded square, knocked-out cross
    hospital: '<rect x="3" y="3" width="18" height="18" rx="4.5" fill="{c}"/>' +
      '<path d="M12 7.5v9M7.5 12h9" stroke="{k}" stroke-width="2.8"/>',
    // ANIMAL: paw print (animal shelter / livestock)
    animal: '<g fill="{c}" stroke="none"><ellipse cx="5" cy="10.5" rx="2.1" ry="2.6"/>' +
      '<ellipse cx="9.2" cy="5.8" rx="2.1" ry="2.6"/><ellipse cx="14.8" cy="5.8" rx="2.1" ry="2.6"/>' +
      '<ellipse cx="19" cy="10.5" rx="2.1" ry="2.6"/></g>' +
      '<path d="M12 12.5c-3 0-6 3.6-6 6.1 0 1.5 1.2 2.1 2.5 2.1 1.4 0 2.2-.8 3.5-.8s2.1.8 3.5.8c1.3 0 2.5-.6 2.5-2.1 0-2.5-3-6.1-6-6.1z" fill="{c}"/>',
    // SMOKE: cloud with haze lines (air quality)
    smoke: '<path d="M7 14.5a3.8 3.8 0 0 1 .4-7.6 5 5 0 0 1 9.6 1.4 3.2 3.2 0 0 1-.4 6.2z" fill="{c}"/>' +
      '<path d="M4 18.5h9M16 18.5h4M7 21.5h10"/>',
    // INFO: methodology
    info: '<circle cx="12" cy="12" r="9.5" fill="{c}"/>' +
      '<path d="M12 11v6" stroke="{k}" stroke-width="2.4"/>' +
      '<circle cx="12" cy="7.6" r="1.4" fill="{k}" stroke="none"/>',
    // EXTERNAL: drawn heavier so it survives at 12px
    external: '<path d="M14 3.5h6.5V10M20.5 3.5L11 13M18 14v5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 19V8a1.5 1.5 0 0 1 1.5-1.5h5" stroke-width="2.6"/>',
    // CHECK: address check
    check: '<circle cx="12" cy="12" r="9.5" fill="{c}"/>' +
      '<path d="M7.6 12.4l3 3 5.8-6.3" stroke="{k}" stroke-width="2.4"/>',
    // LOCATE: geolocation crosshair
    locate: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.6" fill="{c}" stroke="none"/>' +
      '<path d="M12 1.5V5M12 19v3.5M1.5 12H5M19 12h3.5"/>',
    // DANGER: header alert triangle
    danger: '<path d="M10.3 3.9L1.9 18.2A2 2 0 0 0 3.6 21h16.8a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0z" fill="{c}"/>' +
      '<path d="M12 9v4.6" stroke="{k}" stroke-width="2.4"/>' +
      '<circle cx="12" cy="17.2" r="1.3" fill="{k}" stroke="none"/>',
    // TIMELINE: clock
    timeline: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
    // LIVE: solid dot + pulsing ring (ICONS_CSS animates .ic-pulse)
    live: '<circle class="ic-pulse" cx="12" cy="12" r="9" stroke-width="1.6"/>' +
      '<circle cx="12" cy="12" r="5" fill="{c}" stroke="none"/>'
  };

  var ROOT = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"';

  function fill(markup, c, k) { return markup.split('{c}').join(c).split('{k}').join(k); }
  function haloOf(markup) {
    // white copy underneath: same geometry, uniform 4.5px stroke, no animation class
    return '<g class="ic-h" stroke="#fff" stroke-width="4.5">' +
      fill(markup, '#fff', '#fff').replace(/ stroke-width="[^"]*"/g, '').replace(/ class="ic-pulse"/g, '') + '</g>';
  }
  function countText(n, color) {
    var s = n > 99 ? '99+' : String(Math.max(0, n | 0));
    var fs = s.length === 1 ? 11 : s.length === 2 ? 9.5 : 7.5;
    return '<text x="12" y="10.5" text-anchor="middle" dominant-baseline="central" ' +
      'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif" font-weight="800" font-size="' + fs +
      '" fill="' + color + '" stroke="none">' + s + '</text>';
  }
  // panel / plain glyph: currentColor + white halo
  function plain(key, extraClass) {
    var m = G[key];
    return '<svg class="ic ic-' + key + (extraClass ? ' ' + extraClass : '') + '" ' + ROOT + '>' +
      haloOf(m) + '<g class="ic-g">' + fill(m, 'currentColor', '#fff') + '</g></svg>';
  }

  var ICONS = {};
  Object.keys(G).forEach(function (k) { if (k !== 'post') ICONS[k] = plain(k, k === 'external' ? 'ic-12' : ''); });
  ICONS.post = function (n) {
    var m = G.post;
    return '<svg class="ic ic-post" ' + ROOT + '>' + haloOf(m) + '<g class="ic-g">' +
      fill(m, 'currentColor', '#fff') + countText(n, '#fff') + '</g></svg>';
  };
  ICONS.palette = P;

  window.ICONS = ICONS;

  window.ICONS_CSS = [
    '.ic{display:inline-block;width:1em;height:1em;vertical-align:-0.15em;overflow:visible;flex:none}',
    '.ic-12{width:12px;height:12px}.ic-18{width:18px;height:18px}.ic-22{width:22px;height:22px}.ic-28{width:28px;height:28px}',
    '.ic .ic-h{opacity:var(--ic-halo,.92)}',
    '.ic-dark .ic .ic-h{opacity:var(--ic-halo-dark,.14)}',
    '.ic-marker{box-sizing:border-box;display:flex;align-items:center;justify-content:center;border:2px solid #fff;' +
      'border-radius:28%;color:#fff;box-shadow:0 1px 2px rgba(11,13,16,.35),0 3px 8px rgba(11,13,16,.25)}',
    '.ic-marker .ic-glyph{width:66%;height:66%;overflow:visible;transform-origin:50% 50%}',
    '.ic-marker.ic-round{border-radius:50%}',
    '.ic-pulse{transform-origin:12px 12px;transform-box:view-box;animation:ic-pulse 1.6s ease-out infinite}',
    '@keyframes ic-pulse{0%{transform:scale(.55);opacity:.9}70%{transform:scale(1.15);opacity:0}100%{transform:scale(1.15);opacity:0}}',
    '@media (prefers-reduced-motion:reduce){.ic-pulse{animation:none;opacity:.5}}'
  ].join('\n');

  // Leaflet divIcon HTML: color-filled rounded badge, white border + shadow, glyph in white.
  // key may be 'post:12' to render a count bubble.
  window.iconMarkerHTML = function (key, color, size) {
    color = color || P.ink; size = size || 28;
    var parts = String(key).split(':'), k = parts[0], m = G[k];
    if (!m) return '';
    var inner = fill(m, '#fff', color) + (k === 'post' ? countText(+parts[1] || 0, color) : '');
    var round = (k === 'live' || k === 'front' || k === 'locate') ? ' ic-round' : '';
    return '<div class="ic-marker ic-m-' + k + round + '" style="width:' + size + 'px;height:' + size +
      'px;background:' + color + '"><svg class="ic-glyph" ' + ROOT.replace('stroke="currentColor"', 'stroke="#fff"') +
      '>' + inner + '</svg></div>';
  };

  // Panel glyph tinted with a palette color (or any CSS color). key may be 'post:12'.
  window.iconSVG = function (key, color) {
    var parts = String(key).split(':'), k = parts[0];
    var svg = k === 'post' ? ICONS.post(+parts[1] || 0) : ICONS[k];
    if (!svg) return '';
    return color ? svg.replace('<svg class="ic', '<svg style="color:' + color + '" class="ic') : svg;
  };
})();
