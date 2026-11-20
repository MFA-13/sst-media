import json
import base64
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

W, H = 1080, 1350

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1080px; height:1350px; font-family:'Inter', sans-serif; }
.slide { width:1080px; height:1350px; padding:96px 92px; display:flex; flex-direction:column; position:relative; overflow:hidden; color:#F6F1E7; }
.dark { background:#14213D; }
.light { background:#1C2D52; }
.brand { font-size:30px; font-weight:700; letter-spacing:0.5px; opacity:0.9; color:#F6F1E7; display:flex; align-items:center; gap:14px; }
.body { flex:1; display:flex; flex-direction:column; justify-content:center; }
.hook { font-size:92px; line-height:1.04; font-weight:800; letter-spacing:-2px; }
.big { font-size:70px; line-height:1.12; font-weight:750; letter-spacing:-1px; }
.text { font-size:46px; line-height:1.32; font-weight:500; margin-top:36px; opacity:0.92; }
.stat { font-size:190px; font-weight:800; letter-spacing:-6px; line-height:1; color:#F2B134; }
.statlabel { font-size:44px; font-weight:600; margin-top:18px; line-height:1.3; }
.accent { color:#F2B134; }
.foot { display:flex; justify-content:space-between; align-items:flex-end; font-size:28px; font-weight:600; opacity:0.75; }
.swipe { font-size:34px; font-weight:700; opacity:0.9; }
.sources { font-size:30px; line-height:1.45; font-weight:500; }
.sources h3 { font-size:40px; margin-bottom:28px; font-weight:800; }
.sources li { margin-bottom:18px; margin-left:30px; }
.cta-url { font-size:62px; font-weight:800; margin-top:44px; text-decoration:underline; text-decoration-color:#F2B134; text-decoration-thickness:6px; text-underline-offset:12px; }
.bar { position:absolute; left:0; bottom:0; height:14px; background:#E07A1F; z-index:3; }
.photo { position:absolute; inset:0; background-size:cover; background-position:center; z-index:0; }
.shade { position:absolute; inset:0; z-index:1; background:linear-gradient(180deg, rgba(20,33,61,.45) 0%, rgba(20,33,61,.35) 25%, rgba(20,33,61,.6) 50%, rgba(20,33,61,.96) 78%); }
.slide > .brand, .slide > .body, .slide > .foot { position:relative; z-index:2; }
.hasphoto .body { justify-content:flex-end; padding-bottom:40px; }
"""


def day_chart_svg(c):
    # c: {"bands":[[start_hr,end_hr,label,color]], "lines":[{"name","color","pts":[24 values 0-1]}], "note"}
    W, H, L, R, T, B = 896, 600, 20, 20, 70, 70
    pw, ph = W - L - R, H - T - B
    x = lambda h: L + pw * h / 24
    y = lambda v: T + ph * (1 - v)
    out = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Inter,sans-serif">']
    for a, b, lab, col in c.get("bands", []):
        out.append(f'<rect x="{x(a)}" y="{T}" width="{x(b)-x(a)}" height="{ph}" fill="#F6F1E7" opacity="{0.07 if col=='#F6F1E7' else 0.16}"/>')
        out.append(f'<text x="{(x(a)+x(b))/2}" y="{T-22}" fill="{col}" font-size="{c.get("band_font", 34)}" font-weight="800" text-anchor="middle">{lab}</text>')
    out.append(f'<line x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}" stroke="#F6F1E7" stroke-opacity="0.5" stroke-width="2"/>')
    for h, lab in [(0, "12am"), (6, "6am"), (12, "noon"), (18, "6pm"), (24, "12am")]:
        anchor = "start" if h == 0 else "end" if h == 24 else "middle"
        out.append(f'<text x="{x(h)}" y="{T+ph+44}" fill="#F6F1E7" fill-opacity="0.75" font-size="26" font-weight="600" text-anchor="{anchor}">{lab}</text>')
    for ar in c.get("areas", []):
        lo, hi = ar["range"]
        top = [(x(i + 0.5), y(v)) for i, v in enumerate(ar["top"]) if lo <= i <= hi]
        bot = [(x(i + 0.5), y(v)) for i, v in enumerate(ar["bottom"]) if lo <= i <= hi][::-1]
        poly = " ".join(f"{a:.1f},{b:.1f}" for a, b in top + bot)
        out.append(f'<polygon points="{poly}" fill="{ar["color"]}" opacity="0.85"/>')
    for ln in c.get("lines", []):
        pts = ln["pts"]
        hx = (lambda i: i + 0.5) if len(pts) == 24 else (lambda i, k=len(pts) - 1: 24 * i / k)
        d = " ".join(f'{"M" if i == 0 else "L"}{x(hx(i)):.1f},{y(v):.1f}' for i, v in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{ln["color"]}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>')
    out.append('</svg>')
    legend = "".join(f'<span style="display:inline-flex;align-items:center;gap:12px;margin-right:36px"><span style="width:44px;height:9px;border-radius:5px;background:{ln["color"]}"></span>{ln["name"]}</span>' for ln in c.get("lines", []) + c.get("legend_extra", []))
    return "".join(out) + f'<div style="font-size:30px;font-weight:600;margin-top:26px">{legend}</div>' + (f'<div style="font-size:24px;opacity:0.7;margin-top:14px">{c["note"]}</div>' if c.get("note") else "")


def stack_chart_svg(c):
    # c: {"bars":[{"label", "parts":[values]}], "series":[{"name","color"}], "note"}
    W, H, T, B = 896, 560, 20, 125
    ph = H - T - B
    n = len(c["bars"]); bw = 190 if n <= 3 else 165; gap = (W - n * bw) / (n + 1)
    mx = max(sum(b["parts"]) for b in c["bars"])
    out = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Inter,sans-serif">']
    for i, b in enumerate(c["bars"]):
        x0 = gap + i * (bw + gap); y0 = T + ph
        for v, se in zip(b["parts"], c["series"]):
            h = ph * v / mx
            if h > 0:
                out.append(f'<rect x="{x0}" y="{y0-h}" width="{bw}" height="{h}" fill="{se["color"]}" stroke="#14213D" stroke-width="4"/>')
            y0 -= h
        lines = b["label"].split("|")
        tsp = "".join(f'<tspan x="{x0+bw/2}" dy="{0 if j == 0 else 34}">{t}</tspan>' for j, t in enumerate(lines))
        out.append(f'<text x="{x0+bw/2}" y="{T+ph+42}" fill="{b.get("color", "#F6F1E7")}" font-size="{32 if n <= 3 else 28}" font-weight="700" text-anchor="middle">{tsp}</text>')
    out.append('</svg>')
    legend = "".join(f'<div style="display:flex;align-items:center;gap:14px;margin-top:10px"><span style="width:30px;height:30px;border-radius:4px;background:{se["color"]}"></span>{se["name"]}</div>' for se in c["series"])
    return "".join(out) + f'<div style="font-size:30px;font-weight:600;margin-top:22px">{legend}</div>' + (f'<div style="font-size:24px;opacity:0.7;margin-top:14px">{c["note"]}</div>' if c.get("note") else "")


def floor_chart_svg(c):
    # c: {"pts":[0-1 values], "floor":0-1, "floor_label", "xlab":[left,right], "ylab", "note"}
    W, H, L, R, T, B = 896, 560, 20, 20, 30, 70
    pw, ph = W - L - R, H - T - B
    pts = c["pts"]; k = len(pts) - 1
    x = lambda i: L + pw * i / k
    y = lambda v: T + ph * (1 - v)
    d = " ".join(f'{"M" if i == 0 else "L"}{x(i):.1f},{y(v):.1f}' for i, v in enumerate(pts))
    fy = y(c["floor"])
    out = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Inter,sans-serif">',
           f'<line x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}" stroke="#F6F1E7" stroke-opacity="0.5" stroke-width="2"/>',
           f'<line x1="{L}" y1="{fy}" x2="{L+pw}" y2="{fy}" stroke="#F2B134" stroke-width="4" stroke-dasharray="14 12"/>',
           f'<text x="{L+pw}" y="{fy-20}" fill="#F2B134" font-size="34" font-weight="800" text-anchor="end">{c["floor_label"]}</text>',
           f'<path d="{d}" fill="none" stroke="#F6F1E7" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>',
           f'<text x="{L}" y="{T+ph+46}" fill="#F6F1E7" fill-opacity="0.75" font-size="28" font-weight="600">{c["xlab"][0]}</text>',
           f'<text x="{L+pw}" y="{T+ph+46}" fill="#F6F1E7" fill-opacity="0.75" font-size="28" font-weight="600" text-anchor="end">{c["xlab"][1]}</text>',
           f'<text x="{L+pw}" y="{T+10}" text-anchor="end" fill="#F6F1E7" fill-opacity="0.75" font-size="28" font-weight="600">{c["ylab"]}</text>',
           '</svg>']
    return "".join(out) + (f'<div style="font-size:24px;opacity:0.7;margin-top:22px">{c["note"]}</div>' if c.get("note") else "")


def slide_html(s, i, n):
    theme = s.get("theme", "light")
    if theme == "sun": theme = "dark"
    inner = ""
    kind = s["kind"]
    if kind == "hook":
        inner = f'<div class="hook">{s["text"]}</div>'
        if s.get("sub"):
            inner += f'<div class="text">{s["sub"]}</div>'
    elif kind == "big":
        inner = f'<div class="big">{s["text"]}</div>'
        if s.get("sub"):
            inner += f'<div class="text">{s["sub"]}</div>'
    elif kind == "stat":
        inner = (f'<div class="big">{s["pre"]}</div><div class="stat" style="margin-top:40px">' if s.get("pre") else '<div class="stat">') + f'{s["stat"]}</div><div class="statlabel">{s["label"]}</div>'
        if s.get("sub"):
            inner += f'<div class="text">{s["sub"]}</div>'
    elif kind == "chart":
        inner = f'<div class="big" style="font-size:60px;margin-bottom:56px">{s["text"]}</div>' + {"stack": stack_chart_svg, "floor": floor_chart_svg}.get(s["chart"].get("type"), day_chart_svg)(s["chart"])
    elif kind == "cta":
        inner = f'<div class="big">{s["text"]}</div><div class="cta-url">{s["url"]}</div>'
        if s.get("sub"):
            inner += f'<div class="text">{s["sub"]}</div>'
    elif kind == "sources":
        items = "".join(f"<li>{x}</li>" for x in s["items"])
        inner = f'<div class="sources"><h3>Sources</h3><ul>{items}</ul><p style="margin-top:36px">{s.get("note","")}</p></div>'
    bg = s.get("bg")
    photo = ""
    if bg == "standin":
        photo = '<div class="standin"></div><div class="shade"></div>'
    elif bg:
        data = base64.b64encode(Path(bg).read_bytes()).decode()
        photo = f'<div class="photo" style="background-image:url(data:image/jpeg;base64,{data})"></div><div class="shade"></div>'
    if bg:
        theme += " hasphoto"
    swipe = '<div class="swipe">Swipe &rarr;</div>' if i < n else '<div></div>'
    progress = f'<div class="bar" style="width:{int(1080*i/n)}px"></div>'
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head>
<body><div class='slide {theme}'>{photo}{progress}
<div class='brand'><svg width="40" height="40" viewBox="0 0 40 40"><circle cx="20" cy="20" r="8" fill="#F2B134"/><g stroke="#F2B134" stroke-width="3" stroke-linecap="round"><line x1="20" y1="3" x2="20" y2="8"/><line x1="20" y1="32" x2="20" y2="37"/><line x1="3" y1="20" x2="8" y2="20"/><line x1="32" y1="20" x2="37" y2="20"/><line x1="8" y1="8" x2="11.5" y2="11.5"/><line x1="28.5" y1="28.5" x2="32" y2="32"/><line x1="8" y1="32" x2="11.5" y2="28.5"/><line x1="28.5" y1="11.5" x2="32" y2="8"/></g></svg>Solar Straight Talk</div>
<div class='body'>{inner}</div>
<div class='foot'><div>{i} / {n}</div>{swipe}</div>
</div></body></html>"""


def render(spec_path, out_dir):
    spec = json.loads(Path(spec_path).read_text())
    out = Path(out_dir) / spec["id"]
    out.mkdir(parents=True, exist_ok=True)
    slides = spec["slides"]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        page = browser.new_page(viewport={"width": W, "height": H})
        for i, s in enumerate(slides, 1):
            page.set_content(slide_html(s, i, len(slides)))
            page.wait_for_timeout(150)
            page.screenshot(path=str(out / f"{spec['id']}_{i:02d}.png"))
        browser.close()
    print(out)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
