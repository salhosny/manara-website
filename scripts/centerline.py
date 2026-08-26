#!/usr/bin/env python3
"""Skeletonize line-art JPG and output a stroke SVG for dashoffset animation."""
import cv2
import numpy as np
import sys


def morphological_skeleton(binary):
    """Proper morphological skeleton via iterative erosion."""
    img = binary.copy()
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    skel = np.zeros(img.shape, np.uint8)
    while True:
        eroded = cv2.erode(img, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img, temp)
        skel = cv2.bitwise_or(skel, temp)
        img = eroded.copy()
        if cv2.countNonZero(img) == 0:
            break
    return skel


def trace_skeleton(skel):
    """Walk skeleton pixels into an ordered path via greedy nearest-neighbor."""
    ys, xs = np.where(skel > 0)
    if len(xs) == 0:
        return []

    pixels = set(zip(xs.tolist(), ys.tolist()))
    h, w = skel.shape

    # Start: bottom-left region (highest y, lowest x)
    max_y = max(y for _, y in pixels)
    candidates = sorted([(x, y) for x, y in pixels if y > max_y - 20], key=lambda p: p[0])
    start = candidates[0]

    visited = set()
    path = [start]
    visited.add(start)

    def get_neighbors(x, y):
        result = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nb = (x + dx, y + dy)
                if nb in pixels and nb not in visited:
                    result.append(nb)
        return result

    current = start
    while True:
        nbrs = get_neighbors(*current)
        if not nbrs:
            # Jump to nearest unvisited pixel
            remaining = [p for p in pixels if p not in visited]
            if not remaining:
                break
            cx, cy = current
            nearest = min(remaining, key=lambda p: (p[0]-cx)**2 + (p[1]-cy)**2)
            # Only jump if reasonably close
            dist = ((nearest[0]-cx)**2 + (nearest[1]-cy)**2) ** 0.5
            if dist > 15:
                break
            current = nearest
        else:
            # Prefer direction of travel
            if len(path) > 1:
                dx = path[-1][0] - path[-2][0]
                dy = path[-1][1] - path[-2][1]
                nbrs.sort(key=lambda n: -((n[0]-current[0])*dx + (n[1]-current[1])*dy))
            current = nbrs[0]
        visited.add(current)
        path.append(current)

    return path


def rdp(points, tol=2.0):
    """Ramer-Douglas-Peucker simplification."""
    if len(points) < 3:
        return list(points)
    x1, y1 = points[0]
    x2, y2 = points[-1]
    dx, dy = x2 - x1, y2 - y1
    length = (dx*dx + dy*dy) ** 0.5

    max_d, idx = 0, 0
    for i in range(1, len(points) - 1):
        x0, y0 = points[i]
        if length > 0:
            d = abs(dy*x0 - dx*y0 + x2*y1 - y2*x1) / length
        else:
            d = ((x0-x1)**2 + (y0-y1)**2) ** 0.5
        if d > max_d:
            max_d, idx = d, i

    if max_d > tol:
        return rdp(points[:idx+1], tol)[:-1] + rdp(points[idx:], tol)
    return [points[0], points[-1]]


def main():
    img_path = sys.argv[1] if len(sys.argv) > 1 else \
        "Images/light-bulb-in-head-in-one-single-continuous-one-line-drawing-simple-lineart-concept-of-idea-and-imagine-illustration-vector.jpg"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "Images/bulb-centerline.svg"
    scale_down = 300  # work at this max dimension

    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    scale = scale_down / max(h, w)
    sw, sh = int(w * scale), int(h * scale)

    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
    _, binary = cv2.threshold(small, 180, 255, cv2.THRESH_BINARY_INV)

    # Clean up noise
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

    print(f"Working at {sw}x{sh}, foreground pixels: {cv2.countNonZero(binary)}")
    print("Computing skeleton...")
    skel = morphological_skeleton(binary)
    print(f"Skeleton pixels: {cv2.countNonZero(skel)}")

    print("Tracing path...")
    path = trace_skeleton(skel)
    print(f"Path points: {len(path)}")

    simplified = rdp(path, tol=1.5)
    print(f"Simplified: {len(simplified)} points")

    # Scale back to original image size
    inv = 1.0 / scale
    pts = [(x * inv, y * inv) for x, y in simplified]

    d = f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"
    for x, y in pts[1:]:
        d += f" L {x:.1f},{y:.1f}"

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n'
           f'  <path fill="none" stroke="#1B2A4A" stroke-width="6"\n'
           f'        stroke-linecap="round" stroke-linejoin="round"\n'
           f'        d="{d}"/>\n'
           f'</svg>\n')

    with open(out_path, 'w') as f:
        f.write(svg)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
