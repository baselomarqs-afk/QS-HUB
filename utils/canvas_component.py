# LEGACY: This module was a Streamlit component. Not used in the new React/FastAPI architecture.
"""
مكون لوحة الرسم التفاعلية (HTML5 Canvas Component)
لوحة رسم تفاعلية مدمجة في Streamlit تسمح للمهندس بمعايرة المقياس تفاعلياً بالنقر، ومراجعة طبقات التظليل البصري للكميات.
"""
import json
import base64
import numpy as np
import cv2
import streamlit as st


def numpy_to_base64(img_array: np.ndarray) -> str:
    """Converts a numpy image array to base64 PNG string."""
    _, buffer = cv2.imencode('.png', img_array)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/png;base64,{b64_str}"


def render_interactive_canvas(
    page_image_array: np.ndarray,
    rooms: list = None,
    walls: list = None,
    columns: list = None,
    width: int = 900,
    height: int = 700
):
    """
    Renders an HTML5 Canvas iframe inside Streamlit.
    - Draws the background drawing image.
    - Highlights rooms, walls, columns as transparent colored overlays.
    - Allows interactive 2-point scale calibration via parent query parameter redirection.
    """
    rooms = rooms or []
    walls = walls or []
    columns = columns or []
    
    # Compress/resize image if too large to fit in canvas
    h, w = page_image_array.shape[:2]
    scale_w = width / w
    scale_h = height / h
    scale_factor = min(scale_w, scale_h, 1.0)
    
    new_w = int(w * scale_factor)
    new_h = int(h * scale_factor)
    resized_img = cv2.resize(page_image_array, (new_w, new_h))
    
    # Scale coordinates to fit canvas dimensions
    scaled_rooms = []
    for r in rooms:
        scaled_rooms.append({
            "x": int(r.get("x", 0) * scale_factor),
            "y": int(r.get("y", 0) * scale_factor),
            "w": int(r.get("w", 0) * scale_factor),
            "h": int(r.get("h", 0) * scale_factor),
            "label": f"{r.get('area_m2', 0)}m²"
        })
        
    scaled_walls = []
    for wl in walls:
        scaled_walls.append({
            "x1": int(wl.get("x1", 0) * scale_factor),
            "y1": int(wl.get("y1", 0) * scale_factor),
            "x2": int(wl.get("x2", 0) * scale_factor),
            "y2": int(wl.get("y2", 0) * scale_factor),
            "label": f"{wl.get('length_m', 0)}m"
        })
        
    scaled_columns = []
    for c in columns:
        scaled_columns.append({
            "x": int(c.get("x", 0) * scale_factor),
            "y": int(c.get("y", 0) * scale_factor),
            "w": int(c.get("w", 0) * scale_factor),
            "h": int(c.get("h", 0) * scale_factor),
            "label": f"{c.get('width_m', 0)}x{c.get('height_m', 0)}"
        })

    img_b64 = numpy_to_base64(resized_img)
    
    # HTML & JavaScript Component
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                overflow: hidden;
                background-color: #f1f5f9;
            }}
            #container {{
                position: relative;
                width: {new_w}px;
                height: {new_h}px;
                border: 2px solid #cbd5e1;
                border-radius: 8px;
                box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            }}
            canvas {{
                position: absolute;
                left: 0;
                top: 0;
                cursor: crosshair;
            }}
            #controls {{
                position: absolute;
                bottom: 10px;
                left: 10px;
                background: rgba(255, 255, 255, 0.95);
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                pointer-events: none;
            }}
        </style>
    </head>
    <body>
        <div id="container">
            <canvas id="paintCanvas" width="{new_w}" height="{new_h}"></canvas>
            <div id="controls">
                <b>📏 معايرة المقياس (Scale Calibration):</b> انقر على نقطتين لتحديد مسافة هندسية معروفة.
            </div>
        </div>

        <script>
            const canvas = document.getElementById('paintCanvas');
            const ctx = canvas.getContext('2d');
            
            const rooms = {json.dumps(scaled_rooms)};
            const walls = {json.dumps(scaled_walls)};
            const columns = {json.dumps(scaled_columns)};
            const scaleFactor = {scale_factor};

            const img = new Image();
            img.src = "{img_b64}";
            img.onload = function() {{
                drawAll();
            }};

            let clickCount = 0;
            let p1 = null;
            let p2 = null;

            function drawAll() {{
                // 1. Draw PDF Page Image
                ctx.drawImage(img, 0, 0, {new_w}, {new_h});
                
                // 2. Draw Rooms Overlay (Semi-transparent Green)
                rooms.forEach(r => {{
                    ctx.fillStyle = "rgba(74, 222, 128, 0.35)"; // green
                    ctx.fillRect(r.x, r.y, r.w, r.h);
                    ctx.strokeStyle = "rgba(34, 197, 94, 0.8)";
                    ctx.lineWidth = 1;
                    ctx.strokeRect(r.x, r.y, r.w, r.h);
                    
                    // Add text
                    ctx.fillStyle = "#166534";
                    ctx.font = "bold 10px Arial";
                    ctx.fillText(r.label, r.x + 5, r.y + 15);
                }});

                // 3. Draw Walls Overlay (Blue lines)
                walls.forEach(w => {{
                    ctx.strokeStyle = "rgba(59, 130, 246, 0.85)"; // blue
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.moveTo(w.x1, w.y1);
                    ctx.lineTo(w.x2, w.y2);
                    ctx.stroke();
                }});

                // 4. Draw Columns (Red rectangles)
                columns.forEach(c => {{
                    ctx.fillStyle = "rgba(239, 68, 68, 0.4)"; // red
                    ctx.fillRect(c.x, c.y, c.w, c.h);
                    ctx.strokeStyle = "rgba(220, 38, 38, 0.9)";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(c.x, c.y, c.w, c.h);
                }});

                // 5. Draw active calibration line if clickCount == 1
                if (clickCount === 1 && p1) {{
                    ctx.fillStyle = "#dc2626";
                    ctx.beginPath();
                    ctx.arc(p1.x, p1.y, 4, 0, 2 * Math.PI);
                    ctx.fill();
                }}
            }}

            canvas.addEventListener('click', function(e) {{
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                if (clickCount === 0) {{
                    p1 = {{ x, y }};
                    clickCount = 1;
                    drawAll();
                }} else if (clickCount === 1) {{
                    p2 = {{ x, y }};
                    clickCount = 0;
                    
                    // Draw line
                    ctx.strokeStyle = "#dc2626";
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.stroke();
                    
                    // Get length in pixels
                    const pxLength = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
                    
                    // Ask user for distance
                    setTimeout(() => {{
                        const meters = prompt("أدخل الطول الحقيقي للمسافة المحددة بالأمتار (Meters):", "5.0");
                        if (meters && !isNaN(meters)) {{
                            const realMeters = parseFloat(meters);
                            // Calculate actual pixels per meter at original image scale
                            const originalPxLength = pxLength / scaleFactor;
                            const calculatedPpm = originalPxLength / realMeters;
                            
                            // Send back to Streamlit by changing parent URL query parameter
                            const parentUrl = new URL(window.parent.location.href);
                            parentUrl.searchParams.set("ppm", calculatedPpm.toFixed(4));
                            window.parent.location.href = parentUrl.toString();
                        }} else {{
                            drawAll();
                        }}
                    }}, 100);
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, width=new_w + 10, height=new_h + 10)
