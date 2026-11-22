import base64
import json
import re
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "renderer"))
from render import day_chart_svg, stack_chart_svg, floor_chart_svg, flow_chart_svg, faucet_svg, _split_accent  # noqa: E402

FPS = 30
W, H = 1080, 1920
SUN = '<svg width="44" height="44" viewBox="0 0 40 40"><circle cx="20" cy="20" r="8" fill="#F2B134"/><g stroke="#F2B134" stroke-width="3" stroke-linecap="round"><line x1="20" y1="3" x2="20" y2="8"/><line x1="20" y1="32" x2="20" y2="37"/><line x1="3" y1="20" x2="8" y2="20"/><line x1="32" y1="20" x2="37" y2="20"/><line x1="8" y1="8" x2="11.5" y2="11.5"/><line x1="28.5" y1="28.5" x2="32" y2="32"/><line x1="8" y1="32" x2="11.5" y2="28.5"/><line x1="28.5" y1="11.5" x2="32" y2="8"/></g></svg>'

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1080px; height:1920px; background:#14213D; font-family:Inter, sans-serif; color:#F6F1E7; overflow:hidden; position:relative; }
.scene { position:absolute; inset:0; opacity:0; }
.box { position:absolute; left:90px; right:110px; top:330px; bottom:400px; display:flex; flex-direction:column; justify-content:center; }
.brand { position:absolute; left:90px; top:200px; font-size:32px; font-weight:700; display:flex; align-items:center; gap:14px; z-index:5; }
.hook { font-size:100px; line-height:1.05; font-weight:800; letter-spacing:-2px; }
.w { display:inline-block; opacity:0; }
.big { font-size:80px; line-height:1.1; font-weight:780; letter-spacing:-1.5px; }
.ctitle { font-size:62px; line-height:1.1; font-weight:800; letter-spacing:-1px; margin-bottom:48px; }
.text { font-size:50px; line-height:1.28; font-weight:600; margin-top:44px; opacity:0; }
.stat { font-size:210px; font-weight:800; letter-spacing:-6px; line-height:1; color:#F2B134; }
.statlabel { font-size:50px; font-weight:650; margin-top:24px; line-height:1.28; opacity:0; }
.accent { color:#F2B134; }
.legend { opacity:0; }
.photo { position:absolute; inset:0; background-size:cover; background-position:center; }
.shade { position:absolute; inset:0; background:linear-gradient(180deg, rgba(20,33,61,.5) 0%, rgba(20,33,61,.35) 30%, rgba(20,33,61,.75) 55%, rgba(20,33,61,.97) 80%); }
.cta-url { font-size:66px; font-weight:800; margin-top:44px; text-decoration:underline; text-decoration-color:#F2B134; text-decoration-thickness:6px; text-underline-offset:12px; }
.sources { font-size:32px; line-height:1.45; font-weight:500; }
.sources h3 { font-size:44px; margin-bottom:28px; font-weight:800; }
.sources li { margin-bottom:18px; margin-left:30px; }
.bar { position:absolute; left:0; bottom:0; height:14px; background:#E07A1F; z-index:5; }
.playhead { position:absolute; top:0; width:4px; background:#F2B134; box-shadow:0 0 18px #F2B134; opacity:0; }
.chartwrap { position:relative; }
"""


def words_html(text):
    # Split hook text into word spans, keeping accent spans yellow.
    out = []
    for part in re.split(r"(<span class=['\"]accent['\"]>.*?</span>|<br>)", _split_accent(text)):
        if not part:
            continue
        if part == "<br>":
            out.append("<br>")
            continue
        m = re.match(r"<span class=['\"]accent['\"]>(.*?)</span>", part)
        cls = "w accent" if m else "w"
        for wd in (m.group(1) if m else part).split():
            out.append(f'<span class="{cls}">{wd}</span>')
    return " ".join(out)


def nwords(html):
    return len(re.sub(r"<[^>]+>", " ", html or "").split())


def parse_stat(s):
    m = re.match(r"^(\D*?)(\d[\d,]*(?:\.\d+)?)(.*)$", s)
    if not m:
        return None
    num = m.group(2)
    return {"pre": m.group(1), "val": float(num.replace(",", "")), "dec": len(num.split(".")[1]) if "." in num else 0,
            "comma": "," in num, "suf": m.group(3)}


def img_url(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / path
    mime = "png" if p.suffix.lower() == ".png" else "jpeg"
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def build(spec):
    slides = [s for i, s in enumerate(spec["slides"]) if i not in spec.get("reel", {}).get("skip", [])]
    scenes, html = [], []
    t = 0.0
    for i, s in enumerate(slides):
        k = s["kind"]
        sid = f"s{i}"
        bg = ""
        if s.get("bg") and s["bg"] != "standin":
            bg = f'<div class="photo" style="background-image:url({img_url(s["bg"])})"></div><div class="shade"></div>'
        if k == "hook":
            n = nwords(s["text"])
            inner = f'<div class="hook">{words_html(s["text"])}</div>'
            if s.get("sub"):
                inner += f'<div class="text">{s["sub"]}</div>'
            dur = 0.3 + n * 0.12 + 1.6 + (1.4 if s.get("sub") else 0)
            box = 'style="justify-content:flex-end"' if bg else ""
            html.append(f'<div class="scene" id="{sid}">{bg}<div class="box" {box}>{inner}</div></div>')
        elif k == "big":
            inner = f'<div class="big">{_split_accent(s["text"])}</div>'
            if s.get("sub"):
                inner += f'<div class="text">{_split_accent(s["sub"])}</div>'
            if s.get("illo"):
                inner += f'<div class="text">{faucet_svg(s["illo"])}</div>'
            dur = min(6.0, max(2.6, (nwords(s["text"]) + nwords(s.get("sub"))) / 4.2 + 1.0))
            html.append(f'<div class="scene" id="{sid}">{bg}<div class="box">{inner}</div></div>')
        elif k == "stat":
            st = parse_stat(s["stat"])
            pre = f'<div class="big" style="margin-bottom:40px">{_split_accent(s["pre"])}</div>' if s.get("pre") else ""
            inner = pre + f'<div class="stat">{s["stat"]}</div><div class="statlabel">{_split_accent(s["label"])}</div>'
            if s.get("sub"):
                inner += f'<div class="text">{s["sub"]}</div>'
            dur = min(6.5, max(3.6, 1.6 + (nwords(s["label"]) + nwords(s.get("sub")) + nwords(s.get("pre"))) / 4.2))
            html.append(f'<div class="scene" id="{sid}" data-stat=\'{json.dumps(st) if st else ""}\'>{bg}<div class="box">{inner}</div></div>')
        elif k == "chart":
            c = s["chart"]
            typ = c.get("type", "day")
            fn = {"stack": stack_chart_svg, "floor": floor_chart_svg, "flow": flow_chart_svg}.get(typ, day_chart_svg)
            body = fn(c)
            cut = body.index("</svg>") + 6
            svg, rest = body[:cut], body[cut:]
            inner = (f'<div class="ctitle">{_split_accent(s["text"])}</div>'
                     f'<div class="chartwrap"><div class="cl">{svg}</div><div class="playhead"></div></div>'
                     f'<div class="legend">{rest}</div>')
            dur = 7.0 if typ == "flow" else 6.0
            html.append(f'<div class="scene" id="{sid}" data-chart="{typ}"><div class="box" style="top:300px;bottom:330px">{inner}</div></div>')
        elif k == "cta":
            inner = f'<div class="big">{s["text"]}</div><div class="cta-url">{s["url"]}</div>'
            if s.get("sub"):
                inner += f'<div class="text">{s["sub"]}</div>'
            dur = 3.2
            html.append(f'<div class="scene" id="{sid}" data-cta="1">{bg}<div class="box" style="justify-content:flex-end">{inner}</div></div>')
        elif k == "sources":
            items = "".join(f"<li>{x}</li>" for x in s["items"])
            inner = f'<div class="sources"><h3>Sources</h3><ul>{items}</ul><p style="margin-top:30px">{s.get("note", "")}</p></div>'
            dur = 3.0
            html.append(f'<div class="scene" id="{sid}"><div class="box">{inner}</div></div>')
        else:
            continue
        scenes.append({"id": sid, "kind": k, "start": round(t, 3), "dur": round(dur, 3), "bg": bool(bg)})
        t += dur
    total = t
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
{''.join(html)}
<div class="brand">{SUN} Solar Straight Talk</div><div id="bar" class="bar"></div>
<script>
const SC = {json.dumps(scenes)}, DUR = {total};
const cl = v => Math.max(0, Math.min(1, v)), seg = (t,a,b) => cl((t-a)/(b-a));
const ease = p => 1 - Math.pow(1-p, 3), io = p => p<.5 ? 4*p*p*p : 1-Math.pow(-2*p+2,3)/2;
const $ = id => document.getElementById(id);
function rise(el, p, dy=36) {{ if (!el) return; el.style.opacity = p; el.style.transform = `translateY(${{(1-p)*dy}}px)`; }}
function fmt(st, v) {{ let s = v.toFixed(st.dec); if (st.comma) s = Number(s).toLocaleString('en-US', {{minimumFractionDigits: st.dec, maximumFractionDigits: st.dec}}); return st.pre + s + st.suf; }}
SC.forEach(s => {{
  const el = $(s.id); s.el = el;
  if (s.kind === 'hook') s.words = [...el.querySelectorAll('.w')];
  if (s.kind === 'stat') {{ const d = el.dataset.stat; s.st = d ? JSON.parse(d) : null; s.num = el.querySelector('.stat'); }}
  if (s.kind === 'chart') {{
    s.typ = el.dataset.chart; s.cl = el.querySelector('.cl'); s.ph = el.querySelector('.playhead');
    const svg = el.querySelector('.cl svg'); s.w = svg.getAttribute('width'); s.h = svg.getAttribute('height');
    s.ph.style.height = s.h + 'px';
  }}
}});
function setT(t) {{
  SC.forEach((s, i) => {{
    const lt = t - s.start, last = i === SC.length - 1;
    const pin = ease(seg(lt, 0, .45)), pout = last ? 0 : ease(seg(lt, s.dur - .35, s.dur));
    const on = lt > -0.01 && lt < s.dur + 0.01;
    s.el.style.opacity = on ? pin * (1 - pout) : 0;
    if (!on) return;
    const sub = s.el.querySelector('.text');
    if (s.kind === 'hook') {{
      s.words.forEach((w, j) => {{
        const a = .25 + j*.12, acc = w.classList.contains('accent');
        const p = ease(seg(lt, a, a + (acc ? .35 : .3)));
        w.style.opacity = p;
        w.style.transform = acc ? `scale(${{1.6 - .6*p}})` : `translateY(${{(1-p)*30}}px)`;
        if (acc) w.style.transformOrigin = 'left center';
      }});
      rise(sub, ease(seg(lt, .4 + s.words.length*.12 + .5, .4 + s.words.length*.12 + 1.0)));
    }} else if (s.kind === 'big') {{
      rise(s.el.querySelector('.big'), pin, 40);
      rise(sub, ease(seg(lt, 1.1, 1.6)));
    }} else if (s.kind === 'stat') {{
      const p = ease(seg(lt, .2, 1.3));
      if (s.st) s.num.textContent = fmt(s.st, s.st.val * p);
      s.num.style.transform = `scale(${{.85 + .15*ease(seg(lt, .1, .6))}})`; s.num.style.transformOrigin = 'left center';
      rise(s.el.querySelector('.statlabel'), ease(seg(lt, 1.0, 1.5)));
      rise(sub, ease(seg(lt, 1.8, 2.3)));
    }} else if (s.kind === 'chart') {{
      const sweep = s.typ === 'flow' ? 4.2 : 3.4;
      const p = io(seg(lt, .6, .6 + sweep));
      if (s.typ === 'stack') {{
        s.cl.style.clipPath = `inset(${{(1-p)*100}}% 0 0 0)`;
      }} else {{
        s.cl.style.clipPath = `inset(0 ${{(1-p)*100}}% 0 0)`;
        s.ph.style.left = (p * s.w - 2) + 'px';
        s.ph.style.opacity = (p > 0 && p < 1) ? .9 : 0;
      }}
      rise(s.el.querySelector('.legend'), ease(seg(lt, .6 + sweep - .4, .6 + sweep + .2)), 20);
    }} else if (s.kind === 'cta') {{
      const ph = s.el.querySelector('.photo'); if (ph) ph.style.transform = `scale(${{1.12 - .1*seg(lt, 0, s.dur)}})`;
      rise(s.el.querySelector('.cta-url'), ease(seg(lt, .5, 1.0)));
      rise(sub, ease(seg(lt, .9, 1.4)));
    }}
    if (s.bg && s.kind !== 'cta') {{ const ph = s.el.querySelector('.photo'); if (ph) ph.style.transform = `scale(${{1.04 + .06*seg(lt, 0, s.dur)}})`; }}
  }});
  $('bar').style.width = (1080 * t / DUR) + 'px';
}}
setT(0);
</script></body></html>"""
    return page, total


def main():
    spec_path = Path(sys.argv[1])
    previews = [float(x) for x in sys.argv[2:]]
    spec = json.loads(spec_path.read_text())
    page, total = build(spec)
    out_dir = ROOT / "rendered/reels"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = Path("/tmp/reel_frames") / spec["id"]
    frames.mkdir(parents=True, exist_ok=True)
    for f in frames.glob("*.jpg"):
        f.unlink()
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        pg = br.new_page(viewport={"width": W, "height": H})
        pg.set_content(page)
        pg.wait_for_timeout(400)
        if previews:
            for t in previews:
                pg.evaluate(f"setT({t})")
                pg.screenshot(path=f"/tmp/rp_{spec['id']}_{t}.png")
            br.close()
            print(f"total {total:.1f}s")
            return
        for i in range(int(total * FPS)):
            pg.evaluate(f"setT({i / FPS})")
            pg.screenshot(path=str(frames / f"{i:05d}.jpg"), type="jpeg", quality=92)
        br.close()
    out = out_dir / f"{spec['id']}_reel.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%05d.jpg"),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-movflags", "+faststart", str(out)], check=True)
    print(out, f"{total:.1f}s")


if __name__ == "__main__":
    main()
