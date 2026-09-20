"""
Composite 4 screenshots into a single high-resolution framed showcase graphic
for the README and documentation.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BRAIN_DIR = Path(r"C:\Users\DHANUSH A G\.gemini\antigravity-ide\brain\b6d08729-f460-40b5-965e-3570b9add9a4")
OUTPUT_DIR = Path(r"c:\Users\DHANUSH A G\Documents\Bharath_Build\docs\assets\screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMG_1 = BRAIN_DIR / "screenshot_1_1789929925648.png"
IMG_2 = BRAIN_DIR / "screenshot_2_1789930025285.png"
IMG_3 = BRAIN_DIR / "screenshot_3_1789930057450.png"
IMG_4 = BRAIN_DIR / "screenshot_4_1789930084415.png"

PANELS = [
    (IMG_1, "01 • Bioluminescent Hero & Floating Pill Navigation"),
    (IMG_2, "02 • Clinical Ingestion Studio & Verified Posology Matrix"),
    (IMG_3, "03 • 24h Chronobiological Bio-Clock & Multilingual Voice Studio"),
    (IMG_4, "04 • Transparent Clinical Membership & Marbled Card ($17/mo)"),
]

def add_browser_frame(img_path: Path, title: str, target_w: int = 900, target_h: int = 560) -> Image.Image:
    raw = Image.open(img_path).convert("RGB")
    # Crop to ratio or resize
    raw_ratio = raw.width / raw.height
    target_ratio = target_w / target_h
    
    if raw_ratio > target_ratio:
        # Wider: crop width
        new_w = int(raw.height * target_ratio)
        offset = (raw.width - new_w) // 2
        cropped = raw.crop((offset, 0, offset + new_w, raw.height))
    else:
        # Taller: crop height from top
        new_h = int(raw.width / target_ratio)
        cropped = raw.crop((0, 0, raw.width, min(new_h, raw.height)))
        
    resized = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Create framed canvas with header bar (34px height)
    bar_h = 36
    framed = Image.new("RGB", (target_w + 4, target_h + bar_h + 4), color=(24, 24, 27)) # Carbon black frame
    draw = ImageDraw.Draw(framed)
    
    # Draw top bar window controls (macOS / browser dots)
    dot_y = bar_h // 2 + 2
    # Red dot
    draw.ellipse((14, dot_y - 5, 24, dot_y + 5), fill=(255, 95, 87))
    # Yellow dot
    draw.ellipse((30, dot_y - 5, 40, dot_y + 5), fill=(254, 188, 46))
    # Green dot
    draw.ellipse((46, dot_y - 5, 56, dot_y + 5), fill=(40, 200, 64))
    
    # Draw Title
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
    
    draw.text((70, dot_y - 7), title, fill=(228, 228, 231), font=font)
    
    # Paste screenshot below header
    framed.paste(resized, (2, bar_h + 2))
    
    # Outer hairline border
    draw.rectangle((0, 0, framed.width - 1, framed.height - 1), outline=(228, 228, 231), width=1)
    
    return framed

def main():
    framed_panels = []
    panel_w, panel_h = 880, 550
    for path, title in PANELS:
        framed = add_browser_frame(path, title, target_w=panel_w, target_h=panel_h)
        framed_panels.append(framed)
    
    # 2x2 Grid with generous padding and dark luxury canvas
    padding = 24
    gap = 20
    header_area = 70
    
    total_w = padding * 2 + (panel_w + 4) * 2 + gap
    total_h = padding * 2 + (panel_h + 40) * 2 + gap + header_area
    
    canvas = Image.new("RGB", (total_w, total_h), color=(10, 15, 20)) # Deep bioluminescent carbon canvas
    draw = ImageDraw.Draw(canvas)
    
    # Master Header text
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        sub_font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        
    draw.text((padding + 4, padding + 4), "BHARAT BUILDS × SUPERPOWER — BIOLUMINESCENT HEALTH COMMAND CENTER", fill=(255, 255, 255), font=title_font)
    draw.text((padding + 4, padding + 36), "Multimodal Clinical Posology Digitization • Real-Time Streaming Vernacular Voice AI • Deterministic Safety Gate", fill=(252, 95, 43), font=sub_font)
    
    # Coordinates for 2x2
    # Panel 0: top-left
    canvas.paste(framed_panels[0], (padding, padding + header_area))
    # Panel 1: top-right
    canvas.paste(framed_panels[1], (padding + framed_panels[0].width + gap, padding + header_area))
    # Panel 2: bottom-left
    canvas.paste(framed_panels[2], (padding, padding + header_area + framed_panels[0].height + gap))
    # Panel 3: bottom-right
    canvas.paste(framed_panels[3], (padding + framed_panels[0].width + gap, padding + header_area + framed_panels[0].height + gap))
    
    out_path = OUTPUT_DIR / "command_center_showcase.png"
    canvas.save(out_path, format="PNG", quality=95)
    print(f"Showcase created successfully: {out_path} ({total_w}x{total_h})")

if __name__ == "__main__":
    main()
