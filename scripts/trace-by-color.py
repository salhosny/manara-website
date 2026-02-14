#!/usr/bin/env python3
"""
Trace PNG to SVG by color separation: use Potrace for accurate outlines,
then fill each region with its original color from the PNG.
Avoids lossy VTracer color quantization.

Decisive-line strategy for textured/jagged edges:
1. Blur the mask before threshold → boundary moves to gradient midpoint,
   smoothing irregular edges into a single decisive line
2. Potrace -a (alphamax) and -O (opttolerance) → smoother curve output
"""
import subprocess
import sys
import tempfile
import os
import re

def get_dominant_colors(image_path, n_colors=10, skip_white=True):
    """Get dominant colors from image using ImageMagick."""
    result = subprocess.run(
        ["magick", image_path, "-colors", str(n_colors), "-unique-colors", "txt:-"],
        capture_output=True, text=True, check=True
    )
    colors = []
    for line in result.stdout.strip().split("\n"):
        if not line or line.startswith("#"):
            continue
        # Format: "0,0: (R,G,B,A)  #RRGGBB  ..."
        match = re.search(r"\((\d+),(\d+),(\d+),(\d+)\)", line)
        if match:
            r, g, b, a = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            if a < 128:
                continue
            if skip_white and r > 220 and g > 220 and b > 220:
                continue
            colors.append((r, g, b))
    return colors[:n_colors]

def trace_color_layer(input_png, color_rgb, output_svg, fuzz=12):
    """Create mask for one color, trace with potrace, return hex_color.
    Uses blur to smooth jagged edges → decisive boundary line.
    """
    r, g, b = color_rgb
    hex_color = f"#{r:02x}{g:02x}{b:02x}"
    
    with tempfile.NamedTemporaryFile(suffix=".pbm", delete=False) as f:
        pbm_path = f.name
    
    try:
        # Create mask: this color -> black, rest -> white
        # Blur before threshold to smooth textured/jagged edges → decisive line
        cmd = [
            "magick", input_png,
            "-background", "white", "-alpha", "remove", "-alpha", "off",
            "-fuzz", f"{fuzz}%",
            "-fill", "black", "-opaque", f"rgb({r},{g},{b})",
            "-fill", "white", "+opaque", "black",
            "-colorspace", "gray",
            "-blur", "0x1.5",  # Soften boundary; threshold picks decisive line
            "-threshold", "50%",
            f"pbm:{pbm_path}"
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Trace with potrace: smooth curves (alphamax), simplify (opttolerance)
        # -a 1.2: smoother corners, less jagged
        # -O 0.5: more curve simplification, fewer segments
        cmd = ["potrace", "-s", "-t", "8", "-a", "1.2", "-O", "0.5", pbm_path, "-o", output_svg]
        subprocess.run(cmd, check=True, capture_output=True)
        
        return hex_color
    except subprocess.CalledProcessError as e:
        print(f"Error tracing color {hex_color}: {e}", file=sys.stderr)
        return None
    finally:
        if os.path.exists(pbm_path):
            os.unlink(pbm_path)

def extract_svg_paths(svg_path, fill_color):
    """Extract path elements and g transform from SVG. Potrace puts fill/transform on g."""
    with open(svg_path) as f:
        content = f.read()
    start = content.find("<svg")
    end = content.find(">", start) + 1
    svg_open = content[start:end]
    # Extract g transform (potrace uses translate+scale)
    g_match = re.search(r'<g ([^>]*)>', content)
    g_attrs = g_match.group(1) if g_match else ""
    # Get transform, replace fill with our color
    transform = ""
    if 'transform=' in g_attrs:
        t_match = re.search(r'transform="([^"]*)"', g_attrs)
        if t_match:
            transform = t_match.group(1)
    raw_paths = re.findall(r'<path ([^>]*)/>', content)
    # Wrap in g with transform and fill, or add fill to each path
    if transform:
        path_str = "\n".join(f'    <path {attrs}/>' for attrs in raw_paths)
        return svg_open, [f'<g transform="{transform}" fill="{fill_color}">\n{path_str}\n  </g>']
    else:
        paths = [f'<path {attrs} fill="{fill_color}"/>' for attrs in raw_paths]
        return svg_open, paths

def main():
    if len(sys.argv) < 3:
        print("Usage: trace-by-color.py <input.png> <output.svg> [n_colors]")
        sys.exit(1)
    
    input_png = sys.argv[1]
    output_svg = sys.argv[2]
    n_colors = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    if not os.path.exists(input_png):
        print(f"Input not found: {input_png}")
        sys.exit(1)
    
    colors = get_dominant_colors(input_png, n_colors=n_colors)
    print(f"Found {len(colors)} colors to trace")
    
    all_paths = []
    svg_header = None
    
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, color in enumerate(colors):
            layer_svg = os.path.join(tmpdir, f"layer_{i}.svg")
            try:
                hex_color = trace_color_layer(input_png, color, layer_svg)
            except Exception:
                hex_color = None
            if hex_color:
                header, paths = extract_svg_paths(layer_svg, hex_color)
                if svg_header is None:
                    svg_header = header
                all_paths.extend(paths)
    
    if not all_paths:
        print("No paths generated")
        sys.exit(1)
    
    # Build output SVG - use first layer's header, add viewBox if missing
    if 'viewBox' not in svg_header:
        svg_header = svg_header.replace('height="598"', 'height="598" viewBox="0 0 644 598"')
    
    with open(output_svg, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(svg_header + "\n")
        for p in all_paths:
            f.write("  " + p + "\n")
        f.write("</svg>\n")
    
    print(f"Wrote {output_svg} with {len(all_paths)} paths")

if __name__ == "__main__":
    main()
