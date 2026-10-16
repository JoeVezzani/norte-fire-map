// Rothermel 1972 surface spread + Anderson 1983 ellipse. Sources in comments. Pure JS.
const RFM = [
 [1,2,2,3,4,5,5,6,7,8,8,8,9,9,10,11,12,12,13,13,14],
 [1,2,2,3,4,5,5,6,7,7,7,8,9,9,10,10,11,12,13,13,13],
 [1,2,2,3,4,5,5,6,6,7,7,8,8,9,9,10,11,12,12,12,13],
 [1,1,2,2,3,4,5,5,6,7,7,8,8,8,9,10,10,11,12,12,13],
 [1,1,2,2,3,4,4,5,6,7,7,8,8,8,9,10,10,11,12,12,13],
 [1,1,2,2,3,4,4,5,6,7,7,8,8,8,9,10,10,11,12,12,12]];
function fineDeadMoisture(tempF, rhPct) {
  const row = Math.min(5, Math.max(0, Math.floor((tempF - 10) / 20)));
  const col = Math.min(20, Math.max(0, Math.floor(rhPct / 5)));
  return RFM[row][col] + 1;
}
const FUELS = {
  SH5: { w: [3.6, 2.1, 0, 2.9], s: [750, 109, 30, 1600], depth: 6.0, mx: 0.15 },
  SH7: { w: [3.5, 5.3, 2.2, 3.4], s: [750, 109, 30, 1600], depth: 6.0, mx: 0.15 },
  '4': { w: [5.01, 4.01, 2.0, 5.01], s: [2000, 109, 30, 1500], depth: 6.0, mx: 0.20 }};
function rothermel(f, m1, mLive) {
  const rp = 32, ST = 0.0555, h = 8000, etaS = 0.174 * Math.pow(0.010, -0.19);
  const cls = f.w.map((t, i) => ({ w: t * 0.0459137, s: f.s[i], m: i < 3 ? m1 + 0.01 * i : mLive, live: i === 3 })).filter(c => c.w > 0);
  const cat = live => {
    const cs = cls.filter(c => c.live === live), A = cs.reduce((a, c) => a + c.s * c.w / rp, 0);
    if (!A) return null;
    const fr = cs.map(c => c.s * c.w / rp / A), sum = g => cs.reduce((a, c, i) => a + fr[i] * g(c), 0);
    return { A, sig: sum(c => c.s), wn: sum(c => c.w * (1 - ST)), M: sum(c => c.m),
      qig: sum(c => Math.exp(-138 / c.s) * (250 + 1116 * c.m)),
      Wfac: cs.reduce((a, c) => a + c.w * Math.exp((live ? -500 : -138) / c.s), 0) };
  };
  const d = cat(false), l = cat(true), AT = d.A + (l ? l.A : 0);
  const fd = d.A / AT, fl = l ? l.A / AT : 0, sigma = fd * d.sig + fl * (l ? l.sig : 0);
  const etaM = r => (r >= 1 ? 0 : 1 - 2.59 * r + 5.11 * r * r - 3.52 * r ** 3);
  const mxL = l ? Math.max(f.mx, 2.9 * (d.Wfac / l.Wfac) * (1 - d.M / f.mx) - 0.226) : 1;
  const wT = cls.reduce((a, c) => a + c.w, 0), beta = wT / (f.depth * rp);
  const bop = 3.348 * Math.pow(sigma, -0.8189), A = 133 * Math.pow(sigma, -0.7913);
  const Gmax = sigma ** 1.5 / (495 + 0.0594 * sigma ** 1.5);
  const G = Gmax * Math.pow(beta / bop, A) * Math.exp(A * (1 - beta / bop));
  const IR = G * h * etaS * (d.wn * etaM(d.M / f.mx) + (l ? l.wn * etaM(l.M / mxL) : 0));
  const xi = Math.exp((0.792 + 0.681 * Math.sqrt(sigma)) * (beta + 0.1)) / (192 + 0.2595 * sigma);
  const sink = (wT / f.depth) * (fd * d.qig + fl * (l ? l.qig : 0));
  return { R0: IR * xi / sink, IR, sigma, beta, bop };
}
function spreadModel({ windMph, windFromDeg, slopePct = 25, rhPct, tempF, fuel = 'SH5', waf = 0.4, liveMoist = 65, upslope = true }) {
  const f = FUELS[fuel] || FUELS.SH5, m1 = fineDeadMoisture(tempF, rhPct) / 100;
  const { R0, IR, sigma, beta, bop } = rothermel(f, m1, liveMoist / 100);
  const C = 7.47 * Math.exp(-0.133 * sigma ** 0.55), B = 0.02526 * sigma ** 0.54, E = 0.715 * Math.exp(-3.59e-4 * sigma);
  let Umid = windMph * waf * 88;
  const Ulim = 96.8 * Math.cbrt(IR);
  const capped = Umid > Ulim; Umid = Math.min(Umid, Ulim);
  const phiW = C * Umid ** B * Math.pow(beta / bop, -E);
  const phiS = upslope ? 5.275 * beta ** -0.3 * (slopePct / 100) ** 2 : 0;
  const Rft = R0 * (1 + phiW + phiS);
  const U = Umid / 88;
  const LB = Math.min(8, Math.max(1.001, 0.936 * Math.exp(0.2566 * U) + 0.461 * Math.exp(-0.1548 * U) - 0.397));
  const s = Math.sqrt(LB * LB - 1), HB = (LB + s) / (LB - s);
  const backRatio = 1 / HB, flankRatio = (1 + backRatio) / (2 * LB);
  const IB = IR * (384 / sigma) * Rft / 60;
  return { headRosChainsPerHr: Rft * 60 / 66, headRosMph: Rft * 60 / 5280, flankRatio, backRatio, lengthToBreadth: LB, flameLengthFt: 0.45 * IB ** 0.46, windFromDeg,
    note: `${fuel}, 1-hr fuel moisture ${Math.round(m1 * 100)}%, live ${liveMoist}%, midflame wind ${U.toFixed(1)} mph` + (capped ? ' (effective wind limit reached)' : '') };
}
function isochrones(frontPoints, model, hours = [1, 2, 3]) {
  const lat0 = frontPoints.reduce((a, p) => a + p[0], 0) / frontPoints.length, r = lat0 * Math.PI / 180;
  const mLat = 111132.92 - 559.82 * Math.cos(2 * r) + 1.175 * Math.cos(4 * r);
  const mLon = 111412.84 * Math.cos(r) - 93.5 * Math.cos(3 * r);
  const dir = ((model.windFromDeg + 180) % 360) * Math.PI / 180, headMph = model.headRosMph * 1609.344;
  const LB = model.lengthToBreadth;
  const hull = pts => {
    pts.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const x = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const p of pts) { while (lo.length > 1 && x(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
    for (const p of pts.slice().reverse()) { while (up.length > 1 && x(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  };
  return hours.map(t => {
    const Dh = headMph * t, Db = Dh * model.backRatio, a = (Dh + Db) / 2, b = a / LB, c = a - Db;
    const verts = [];
    for (const [lat, lon] of frontPoints) for (let k = 0; k < 36; k++) {
      const th = k * Math.PI / 18, x = c + a * Math.cos(th), y = b * Math.sin(th);
      const e = x * Math.sin(dir) + y * Math.cos(dir), n = x * Math.cos(dir) - y * Math.sin(dir);
      verts.push([lat + n / mLat, lon + e / mLon]);
    }
    return { hour: t, headRunMiles: Dh / 1609.344, polygon: hull(verts) };
  });
}
window.spreadModel = spreadModel; window.isochrones = isochrones;
