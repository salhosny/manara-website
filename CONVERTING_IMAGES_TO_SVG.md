# Converting Images to SVGs

This guide explains how to convert PNG/JPG images to SVG icons for the Manara site.

---

## Multi-Color Conversion — Two Methods

### Method A: Color-Separation (Potrace) — Recommended for accuracy

Uses Potrace for accurate outlines, then fills each color region from the original PNG. Avoids lossy quantization—best for icons with subtle fills (e.g. clipboard teal).

**Prerequisites:** ImageMagick, Potrace

```bash
python3 scripts/trace-by-color.py Images/filename.png Images/filename.svg 8
```

The script:
1. Extracts dominant colors from the PNG
2. For each color, creates a mask and traces with Potrace (accurate outlines)
3. **Decisive-line smoothing**: Blurs the mask before threshold so textured/jagged edges become a single clean boundary; uses Potrace `-a 1.2` and `-O 0.5` for smoother curves
4. Fills each traced region with its original color
5. Combines into one SVG with proper layering

### Method B: VTracer (faster, can be lossy)

VTracer preserves colors but may quantize subtle gradients.

```bash
cargo install vtracer
vtracer --input Images/filename.png --output Images/filename.svg --preset poster
```

Post-processing: remove the background path (line 4) and add `viewBox` if needed.

---

## Single-Color Conversion (Potrace)

For black/white silhouettes only.

### Prerequisites

- **ImageMagick** (for preprocessing): `brew install imagemagick`
- **Potrace** (for vectorization): `brew install potrace`

---

## Quick Conversion (Potrace)

### Step 1: Prepare the image

Place your PNG in the `Images/` folder. For best results, use images with:
- Clear contrast between icon and background
- White or transparent background
- Dark or medium-toned icon content

### Step 2: Convert to SVG

Run this command for each image (replace `filename` with your image name):

```bash
magick Images/filename.png -background white -alpha remove -alpha off -colorspace gray -threshold 60% pbm:- | potrace -s -o Images/filename.svg -
```

**Parameters:**
- `-background white -alpha remove -alpha off` — Ensures a solid white background
- `-colorspace gray` — Converts to grayscale
- `-threshold 60%` — Pixels darker than 60% gray become black (traced); lighter become white (ignored). Adjust 40–80% if needed.
- `-s` — Output SVG format

### Step 3: Make the SVG themeable

Replace the black fill with `currentColor` so the icon can inherit CSS color:

```bash
sed -i '' 's/fill="#000000"/fill="currentColor"/g' Images/filename.svg
```

Or edit the SVG and change `fill="#000000"` to `fill="currentColor"` in the `<g>` element.

### Step 4: Use in HTML

Reference the SVG with an `<img>` tag:

```html
<img src="Images/filename.svg" alt="Description" class="service-icon">
```

---

## Batch Conversion Script

To convert all PNGs in `Images/` at once:

```bash
cd /path/to/manara-site
for f in course_builds course_reviews lms_expertise multi_media; do
  magick "Images/${f}.png" -background white -alpha remove -alpha off -colorspace gray -threshold 60% pbm:- | potrace -s -o "Images/${f}.svg" -
  sed -i '' 's/fill="#000000"/fill="currentColor"/g' "Images/${f}.svg"
done
```

---

## Alternative Methods

### AutoTrace (multi-color)

For icons that need multiple colors preserved:
- **Online:** [svg-converter.com/autotrace](https://svg-converter.com/autotrace) — upload, set color count, download
- **CLI:** `npm install autotrace` or `brew install autotrace` (if available)

### Vectorizer.ai (paid API)

High-quality vectorization with an API. See [vectorizer.ai/api](https://vectorizer.ai/api).

### Manual redraw

For pixel-perfect control, redraw in Figma, Inkscape, or Illustrator and export SVG.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Blank or empty SVG | Try a different threshold (e.g. 40% or 80%) |
| Icon traced inside-out | Remove `-negate` if you added it, or adjust threshold |
| Icons not showing in browser | Serve via a local server (`python3 -m http.server 8000`) instead of opening `file://` |
| Wrong shapes traced | Preprocess: increase contrast, remove noise, or use a different source image |

---

## File Structure

```
Images/
├── course_builds.svg
├── course_reviews.svg
├── lms_expertise.svg
└── multi_media.svg
```

---

## Summary

| Method | Effort | Output | Themeability |
|--------|--------|--------|--------------|
| Potrace | Low | Single-color silhouette | `currentColor` or CSS filter |
| AutoTrace | Medium | Multi-color | CSS variables per color |
| Manual | High | Exact | Full control |
| Vectorizer.ai | Low (paid) | High quality | Depends on post-processing |
