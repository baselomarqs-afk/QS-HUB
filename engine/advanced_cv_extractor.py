import cv2
import numpy as np
import math
import os

def process_floor_plan_image(img_path):
    """
    Advanced Computer Vision Extractor for Architectural Floor Plans with Auto-Coloring.
    Uses contour analysis to mathematically extract walls and saves a visual takeoff markup.
    """
    if not os.path.exists(img_path):
        return {"cv_perimeter_px": 0, "cv_area_px": 0, "cv_door_count": 0, "cv_window_count": 0, "wall_internal_px": 0}

    try:
        # Load grayscale image for processing
        img_gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img_gray is None:
            return {"cv_perimeter_px": 0, "cv_area_px": 0, "cv_door_count": 0, "cv_window_count": 0, "wall_internal_px": 0}

        # Load color image for Auto-Coloring Markup
        img_color = cv2.imread(img_path, cv2.IMREAD_COLOR)

        # Invert image (black lines become white)
        _, thresh = cv2.threshold(img_gray, 200, 255, cv2.THRESH_BINARY_INV)

        # 1. Detect Main Walls and Perimeter
        # We assume walls are thick lines. Use morphological closing to merge them.
        kernel = np.ones((5, 5), np.uint8)
        walls = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(walls, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        max_area = 0
        max_perimeter = 0
        largest_cnt = None
        
        # Find the largest bounding contour (the building footprint / external walls)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > max_area:
                max_area = area
                max_perimeter = cv2.arcLength(cnt, True)
                largest_cnt = cnt

        # Auto-Coloring: Draw External Walls (Blue)
        if largest_cnt is not None:
            cv2.drawContours(img_color, [largest_cnt], -1, (255, 0, 0), 4) # BGR: Blue

        # Find internal walls (All other contours inside the main one)
        internal_contours, _ = cv2.findContours(walls, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        total_internal_px = 0
        for cnt in internal_contours:
            # Avoid counting the external contour again and avoid tiny noise
            if cv2.contourArea(cnt) < max_area * 0.9 and cv2.contourArea(cnt) > 100:
                length = cv2.arcLength(cnt, True)
                # An internal wall usually separates 2 rooms, so length is roughly 2x the wall length
                total_internal_px += (length / 2.0)
                # Auto-Coloring: Draw Internal Walls (Green)
                cv2.drawContours(img_color, [cnt], -1, (0, 255, 0), 2) # BGR: Green

        # 2. Detect Doors/Windows (Gaps in Walls)
        # We do this by finding small isolated blobs that represent door swings or window blocks.
        kernel_small = np.ones((3, 3), np.uint8)
        clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_small, iterations=1)
        
        components, _ = cv2.findContours(clean, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        door_count = 0
        window_count = 0
        
        for comp in components:
            comp_area = cv2.contourArea(comp)
            if 50 < comp_area < 5000:
                rect = cv2.minAreaRect(comp)
                width, height = rect[1]
                if width > 0 and height > 0:
                    aspect_ratio = max(width, height) / min(width, height)
                    rect_area = width * height
                    solidity = comp_area / rect_area if rect_area > 0 else 0
                    
                    if 1.0 <= aspect_ratio <= 1.8 and solidity < 0.35:
                        door_count += 1
                        # Auto-Coloring: Highlight Doors (Yellow)
                        box = cv2.boxPoints(rect)
                        box = np.int0(box)
                        cv2.drawContours(img_color, [box], 0, (0, 255, 255), 2)
                    elif aspect_ratio >= 3.0 and 0.15 <= solidity <= 0.85:
                        window_count += 1
                        # Auto-Coloring: Highlight Windows (Orange)
                        box = cv2.boxPoints(rect)
                        box = np.int0(box)
                        cv2.drawContours(img_color, [box], 0, (0, 165, 255), 2)

        # Save the Auto-Colored Takeoff Markup
        markup_path = img_path.replace(".png", "_markup.png")
        cv2.imwrite(markup_path, img_color)
        
        import os
        markup_filename = os.path.basename(markup_path)
        
        return {
            "cv_perimeter_px": max_perimeter,
            "cv_area_px": max_area,
            "cv_door_count": door_count,
            "cv_window_count": window_count,
            "wall_internal_px": total_internal_px,
            "markup_url": f"/cache/{markup_filename}"
        }

    except Exception as e:
        print(f"CV Extractor error: {e}")
        return {"cv_perimeter_px": 0, "cv_area_px": 0, "cv_door_count": 0, "cv_window_count": 0, "wall_internal_px": 0}

