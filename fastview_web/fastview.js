// The fast 3D view of the Worm3DViewer: a Streamlit component (see fastview.py).
//
// Each model's file (made by `python fastview.py -export`) is fetched once and kept
// in the browser's Cache Storage (the file names change when the meshes do). It is
// decoded and handed to the graphics card once. The models that are not shown are
// fetched in the background, so ticking them later is quick. On each Refresh the app
// sends, for each model shown, where it is along x and the color and state of each
// cell (shown, faded or hidden), which go into a small texture: no mesh is rebuilt.
"use strict";

const CACHE = "worm3dviewer-fastview";
const canvas = document.getElementById("view");
const statusEl = document.getElementById("status");
const gl = canvas.getContext("webgl2", { antialias: true });

// -- Streamlit (component protocol v1) ----------------------------------------------

function toStreamlit(type, data) {
  window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
}
window.addEventListener("message", (e) => {
  if (e.data && e.data.type === "streamlit:render") render(e.data.args);
});
toStreamlit("streamlit:componentReady", { apiVersion: 1 });

// -- files: fetch (or read from Cache Storage), gunzip, decode -----------------------

async function getFile(name) {
  const url = "data/" + name;
  let cache = null;
  try {
    cache = await caches.open(CACHE);
    const hit = await cache.match(url);
    if (hit) return await hit.arrayBuffer();
  } catch (e) {} // no Cache Storage: just fetch
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + ": " + r.status);
  const buf = await r.arrayBuffer();
  if (cache) cache.put(url, new Response(buf.slice(0))).catch(() => {});
  return buf;
}

async function gunzip(buf) {
  const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
  return await new Response(stream).arrayBuffer();
}

// The encoding of fastview.encode() (Google's webgl-loader scheme, as bytes)
function decode(buf) {
  const dv = new DataView(buf);
  if (dv.getUint32(0, true) !== 0x31443357) throw new Error("not a W3D1 file");
  const n = dv.getUint32(4, true), nt = dv.getUint32(8, true), bits = dv.getUint8(12);
  const lo = [dv.getFloat32(16, true), dv.getFloat32(20, true), dv.getFloat32(24, true)];
  const scale = dv.getFloat32(28, true) / ((1 << bits) - 1);
  const bytes = new Uint8Array(buf, 32);
  let p = 0;
  const next = () => {
    let b = bytes[p++], v = b & 0x7f, shift = 7;
    while (b & 0x80) {
      b = bytes[p++];
      v |= (b & 0x7f) << shift;
      shift += 7;
    }
    return v;
  };
  const pos = new Float32Array(3 * n);
  for (let j = 0; j < 3; j++) {
    let q = 0;
    for (let i = 0; i < n; i++) {
      const v = next();
      q += (v >>> 1) ^ -(v & 1); // un-zigzag, then undo the difference
      pos[3 * i + j] = lo[j] + q * scale;
    }
  }
  const idx = new Uint32Array(3 * nt);
  let highest = 0;
  for (let i = 0; i < 3 * nt; i++) {
    const v = next();
    idx[i] = highest - v;
    if (v === 0) highest++;
  }
  return { n, pos, idx };
}

function vertexNormals(pos, idx, n) {
  const nr = new Float32Array(3 * n);
  for (let t = 0; t < idx.length; t += 3) {
    const a = 3 * idx[t], b = 3 * idx[t + 1], c = 3 * idx[t + 2];
    const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2];
    const vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
    const x = uy * vz - uz * vy, y = uz * vx - ux * vz, z = ux * vy - uy * vx;
    for (const k of [a, b, c]) { nr[k] += x; nr[k + 1] += y; nr[k + 2] += z; }
  }
  for (let i = 0; i < nr.length; i += 3) {
    const l = Math.hypot(nr[i], nr[i + 1], nr[i + 2]) || 1;
    nr[i] /= l; nr[i + 1] /= l; nr[i + 2] /= l;
  }
  return nr;
}

// -- drawing -------------------------------------------------------------------------

const VS = `#version 300 es
in vec3 aPos; in vec3 aNrm; in uint aCell;
uniform mat4 uProj, uView; uniform float uX, uDpr; uniform sampler2D uCells;
out vec3 vN, vP; flat out uint vCell;
void main() {
  vec4 p = uView * vec4(aPos + vec3(uX, 0.0, 0.0), 1.0);
  gl_Position = uProj * p; vP = p.xyz; vN = mat3(uView) * aNrm; vCell = aCell;
  gl_PointSize = texelFetch(uCells, ivec2(int(aCell), 1), 0).r * 255.0 * uDpr;
}`;
const FS = `#version 300 es
precision highp float;
in vec3 vN, vP; flat in uint vCell;
uniform sampler2D uCells; uniform int uPass, uPoints;
out vec4 color;
void main() {
  vec4 c = texelFetch(uCells, ivec2(int(vCell), 0), 0);
  if (c.a < 0.01 || (uPass == 0) != (c.a > 0.99)) discard; // opaque, then faded
  vec3 n;
  if (uPoints == 1) { // a point drawn as a small sphere
    vec2 d = gl_PointCoord * 2.0 - 1.0;
    if (dot(d, d) > 1.0) discard;
    n = vec3(d.x, -d.y, sqrt(1.0 - dot(d, d)));
  } else {
    n = normalize(vN);
    if (!gl_FrontFacing) n = -n;
  }
  vec3 v = uPoints == 1 ? vec3(0.0, 0.0, 1.0) : normalize(-vP); // the light is at the eye
  float diffuse = abs(dot(n, v));
  float specular = pow(max(dot(reflect(-v, n), v), 0.0), 30.0) * 0.15;
  color = vec4(c.rgb * (0.3 + 0.7 * diffuse) + specular, c.a);
}`;

function compile(type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}
const prog = gl.createProgram();
gl.attachShader(prog, compile(gl.VERTEX_SHADER, VS));
gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FS));
["aPos", "aNrm", "aCell"].forEach((name, i) => gl.bindAttribLocation(prog, i, name));
gl.linkProgram(prog);
if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
const U = {};
for (const u of ["uProj", "uView", "uX", "uDpr", "uCells", "uPass", "uPoints"]) U[u] = gl.getUniformLocation(prog, u);

// A model on the graphics card: its meshes, the cell of each point, and a texture
// with a row of colors and states (alpha) and a row of point sizes, one per cell
class Model {
  constructor(key, decoded, cells) {
    const { n, pos, idx } = decoded;
    this.key = key;
    this.cells = cells;
    this.n = n;
    this.nIdx = idx.length;
    this.points = idx.length === 0;
    this.x = 0;
    this.shown = false;
    this.lo = [Infinity, Infinity, Infinity];
    this.hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < pos.length; i += 3)
      for (let j = 0; j < 3; j++) {
        this.lo[j] = Math.min(this.lo[j], pos[i + j]);
        this.hi[j] = Math.max(this.hi[j], pos[i + j]);
      }
    const cellOf = new Uint16Array(n);
    cells.forEach((c, i) => cellOf.fill(i, c[1], c[1] + c[2]));
    this.vao = gl.createVertexArray();
    gl.bindVertexArray(this.vao);
    const attrib = (loc, data, size, type, integer) => {
      gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(loc);
      if (integer) gl.vertexAttribIPointer(loc, size, type, 0, 0);
      else gl.vertexAttribPointer(loc, size, type, false, 0, 0);
    };
    attrib(0, pos, 3, gl.FLOAT);
    attrib(1, this.points ? new Float32Array(3 * n) : vertexNormals(pos, idx, n), 3, gl.FLOAT);
    attrib(2, cellOf, 1, gl.UNSIGNED_SHORT, true);
    if (!this.points) {
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
    }
    gl.bindVertexArray(null);
    this.table = new Uint8Array(8 * cells.length);
    cells.forEach((c, i) => (this.table[4 * (cells.length + i)] = Math.min(255, c[7])));
    this.tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, cells.length, 2);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  }
  // colors: 6 hex digits per cell; states: one digit per cell, 0 hidden, 1 shown,
  // 2 faded (see fastview.cell_states())
  setState(x, colors, states) {
    this.x = x;
    this.anyFaded = states.includes("2");
    for (let i = 0; i < this.cells.length; i++) {
      for (let j = 0; j < 3; j++) this.table[4 * i + j] = parseInt(colors.substr(6 * i + 2 * j, 2), 16);
      this.table[4 * i + 3] = [0, 255, 13][+states[i]]; // faded: opacity 0.05
    }
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, this.cells.length, 2, gl.RGBA, gl.UNSIGNED_BYTE, this.table);
  }
}

// -- the camera: around a center, at a distance, looking along -dir -----------------

const cam = { center: [0, 0, 0], dist: 1, dir: [1, 0, 0], up: [0, 1, 0], radius: 1 };
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const unit = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
function rotate(v, axis, angle) { // Rodrigues' rotation
  const c = Math.cos(angle), s = Math.sin(angle), k = unit(axis), kv = cross(k, v), d = dot(k, v);
  return [0, 1, 2].map((i) => v[i] * c + kv[i] * s + k[i] * d * (1 - c));
}

// As the app's camera in stpyvista's view: VTK's default direction (looking down
// the z axis) with y up (build_scene's set_viewup), fitted to the models shown as
// VTK's reset_camera does (a 30 degree view angle)
function fitCamera() {
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (const m of shownModels()) for (let j = 0; j < 3; j++) {
    const s = j === 0 ? m.x : 0;
    lo[j] = Math.min(lo[j], m.lo[j] + s);
    hi[j] = Math.max(hi[j], m.hi[j] + s);
  }
  if (!isFinite(lo[0])) return;
  cam.center = [0, 1, 2].map((j) => (lo[j] + hi[j]) / 2);
  cam.radius = Math.max(Math.hypot(...sub(hi, lo)) / 2, 1e-3);
  cam.dist = cam.radius / Math.sin((15 * Math.PI) / 180);
  cam.dir = [0, 0, 1];
  cam.up = [0, 1, 0];
}

function matrices() {
  const eye = cam.center.map((c, j) => c + cam.dir[j] * cam.dist);
  const z = cam.dir, x = unit(cross(cam.up, z)), y = cross(z, x);
  const view = [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, eye), -dot(y, eye), -dot(z, eye), 1];
  const near = Math.max(cam.dist - cam.radius * 3, cam.dist * 0.001), far = cam.dist + cam.radius * 3;
  const t = 1 / Math.tan((15 * Math.PI) / 180), aspect = canvas.width / canvas.height;
  const proj = [t / aspect, 0, 0, 0, 0, t, 0, 0, 0, 0, (far + near) / (near - far), -1, 0, 0, (2 * far * near) / (near - far), 0];
  return { view, proj };
}

// -- drawing on demand ---------------------------------------------------------------

const models = {}; // key -> Model, once loaded
let background = [1, 1, 1];
let drawPending = false;
const shownModels = () => Object.values(models).filter((m) => m.shown);

function requestDraw() {
  if (!drawPending) {
    drawPending = true;
    requestAnimationFrame(draw);
  }
}

function draw() {
  drawPending = false;
  const { view, proj } = matrices();
  gl.viewport(0, 0, canvas.width, canvas.height);
  gl.clearColor(background[0], background[1], background[2], 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.useProgram(prog);
  gl.uniformMatrix4fv(U.uProj, false, proj);
  gl.uniformMatrix4fv(U.uView, false, view);
  gl.uniform1f(U.uDpr, devicePixelRatio);
  gl.uniform1i(U.uCells, 0);
  gl.enable(gl.DEPTH_TEST);
  for (const pass of [0, 1]) {
    if (pass === 1) {
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.depthMask(false);
    }
    gl.uniform1i(U.uPass, pass);
    for (const m of shownModels()) {
      if (pass === 1 && !m.anyFaded) continue;
      gl.bindVertexArray(m.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, m.tex);
      gl.uniform1f(U.uX, m.x);
      gl.uniform1i(U.uPoints, m.points ? 1 : 0);
      if (m.points) gl.drawArrays(gl.POINTS, 0, m.n);
      else gl.drawElements(gl.TRIANGLES, m.nIdx, gl.UNSIGNED_INT, 0);
    }
  }
  gl.disable(gl.BLEND);
  gl.depthMask(true);
}

function resize() {
  const w = Math.round(canvas.clientWidth * devicePixelRatio);
  const h = Math.round(canvas.clientHeight * devicePixelRatio);
  if (w && h && (canvas.width !== w || canvas.height !== h)) {
    canvas.width = w;
    canvas.height = h;
    requestDraw();
  }
}
new ResizeObserver(resize).observe(canvas);

// -- mouse and touch: drag to rotate, right-drag or shift-drag to pan, wheel to zoom --

let drag = null;
canvas.addEventListener("contextmenu", (e) => e.preventDefault());
canvas.addEventListener("pointerdown", (e) => {
  canvas.setPointerCapture(e.pointerId);
  drag = { x: e.clientX, y: e.clientY, pan: e.button === 2 || e.button === 1 || e.shiftKey };
});
canvas.addEventListener("pointerup", () => (drag = null));
canvas.addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  drag.x = e.clientX;
  drag.y = e.clientY;
  if (drag.pan) {
    const right = unit(cross(cam.up, cam.dir));
    const s = (2 * cam.dist * Math.tan((15 * Math.PI) / 180)) / canvas.clientHeight;
    cam.center = cam.center.map((c, j) => c - right[j] * dx * s + cam.up[j] * dy * s);
  } else {
    const right = unit(cross(cam.up, cam.dir));
    cam.dir = rotate(cam.dir, cam.up, -dx * 0.01); // turn around the up direction
    cam.dir = unit(rotate(cam.dir, right, -dy * 0.01)); // and tilt
    cam.up = unit(rotate(cam.up, right, -dy * 0.01));
  }
  requestDraw();
});
canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  cam.dist *= Math.exp(e.deltaY * 0.001);
  requestDraw();
}, { passive: false });

// -- each Refresh: load what is needed, then apply the options -------------------------

const loading = {}; // key -> Promise of its Model
function load(item) {
  if (!loading[item.key]) {
    loading[item.key] = Promise.all([getFile(item.file).then(gunzip), getFile(item.cells)]).then(
      ([raw, cellsBuf]) => {
        const cells = JSON.parse(new TextDecoder().decode(cellsBuf));
        return (models[item.key] = new Model(item.key, decode(raw), cells));
      }
    );
  }
  return loading[item.key];
}

let lastFit = null;
let latest = null;
async function render(args) {
  latest = args;
  canvas.style.height = args.height + "px";
  toStreamlit("streamlit:setFrameHeight", { height: args.height });
  background = [1, 3, 5].map((i) => parseInt(args.background.substr(i, 2), 16) / 255);
  const wanted = args.models.filter((m) => m.states !== undefined);
  statusEl.textContent = wanted.some((m) => !models[m.key]) ? "Loading models…" : "";
  try {
    await Promise.all(wanted.map(load));
  } catch (e) {
    statusEl.textContent = "Could not load the models: " + e.message;
    return;
  }
  if (args !== latest) return; // a newer Refresh came while loading
  statusEl.textContent = "";
  for (const item of args.models) {
    const m = models[item.key];
    if (!m) continue;
    m.shown = item.states !== undefined;
    if (m.shown) m.setState(item.x, item.colors, item.states);
  }
  if (args.fit !== lastFit) {
    lastFit = args.fit;
    fitCamera();
  }
  resize();
  requestDraw();
  // then the other models, in the background, so that ticking them is quick
  for (const item of args.models) if (item.states === undefined) await load(item).catch(() => {});
}
