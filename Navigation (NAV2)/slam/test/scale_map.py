#!/usr/bin/env python3
"""
scale_map.py — Rescale a ROS2 occupancy grid map.

Two modes:
  --resolution NEW_RES   : set exact resolution (m/px), keep image as-is
  --factor SCALE         : multiply resolution by SCALE (>1 = zoom in, <1 = zoom out)

The image is only resized when --resize is passed (optional).
Origin is preserved; update it manually in the output YAML if the robot's
starting position in the real world is different from (0,0).

Examples:
  # You measured 200px = 4.0m in the real room → resolution should be 0.020
  python3 scale_map.py map2mapping7.yaml --resolution 0.020

  # The map is 2x too large → halve the resolution
  python3 scale_map.py map2mapping7.yaml --factor 0.5

  # Scale + also resize the image to keep pixel density consistent
  python3 scale_map.py map2mapping7.yaml --factor 0.5 --resize
"""

import sys
import argparse
import shutil
from pathlib import Path

try:
    import yaml
    from PIL import Image
except ImportError:
    print("Install dependencies: pip3 install pyyaml pillow")
    sys.exit(1)


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("yaml_file", help="Path to the map YAML file")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--resolution", type=float,
                       help="New resolution in m/pixel (e.g. 0.020)")
    group.add_argument("--factor", type=float,
                       help="Scale factor applied to current resolution (0.5 = halve m/px)")
    parser.add_argument("--resize", action="store_true",
                        help="Also resize the image to match the new resolution "
                             "(keeps real-world coverage, changes pixel count)")
    args = parser.parse_args()

    yaml_path = Path(args.yaml_file).resolve()
    meta = load_yaml(yaml_path)
    img_path = yaml_path.parent / meta["image"]

    old_res = float(meta["resolution"])

    if args.resolution:
        new_res = args.resolution
        factor = new_res / old_res      # pixel scale if --resize
    else:
        factor = args.factor
        new_res = old_res * factor

    img = Image.open(img_path)
    old_w, old_h = img.size
    old_w_m = old_w * old_res
    old_h_m = old_h * old_res

    suffix = f"_res{new_res:.5f}".replace(".", "p")
    out_img_name = img_path.stem + suffix + img_path.suffix
    out_yaml_name = yaml_path.stem + suffix + yaml_path.suffix
    out_img_path  = yaml_path.parent / out_img_name
    out_yaml_path = yaml_path.parent / out_yaml_name

    print(f"\nOriginal map:")
    print(f"  Image      : {img_path.name}  ({old_w} × {old_h} px)")
    print(f"  Resolution : {old_res} m/px")
    print(f"  Coverage   : {old_w_m:.2f}m × {old_h_m:.2f}m")
    print(f"  Origin     : {meta['origin']}")

    if args.resize:
        # Resize image so the real-world coverage stays the same but pixel density changes
        new_w = int(round(old_w * (old_res / new_res)))
        new_h = int(round(old_h * (old_res / new_res)))
        scaled = img.resize((new_w, new_h), Image.NEAREST)
        scaled.save(out_img_path)
    else:
        # Keep image identical, only change resolution (real-world coverage changes)
        new_w, new_h = old_w, old_h
        shutil.copy(img_path, out_img_path)

    new_w_m = new_w * new_res
    new_h_m = new_h * new_res

    new_meta = {**meta, "image": out_img_name, "resolution": round(new_res, 6)}
    save_yaml(out_yaml_path, new_meta)

    print(f"\nScaled map:")
    print(f"  Image      : {out_img_name}  ({new_w} × {new_h} px)")
    print(f"  Resolution : {new_res} m/px")
    print(f"  Coverage   : {new_w_m:.2f}m × {new_h_m:.2f}m")
    print(f"  Origin     : {new_meta['origin']}  ← update this if needed")
    print(f"\nOutput YAML : {out_yaml_path}")
    print(f"\nTo use this map:")
    print(f"  ros2 launch robot_hardware real_robot_nav.launch.py map:={out_yaml_path}")
    print(f"\nIf the robot starts at a different real-world position, update 'origin' in:")
    print(f"  {out_yaml_path}")
    print(f"  origin: [x_meters_of_bottom_left_corner, y_meters_of_bottom_left_corner, 0]")


if __name__ == "__main__":
    main()
