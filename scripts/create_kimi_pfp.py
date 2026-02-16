#!/usr/bin/env python3
"""Create a profile picture for kimi k2.5."""
from PIL import Image, ImageDraw, ImageFont
import os

def create_pfp(size=512, output_path="docs/assets/kimi-k25-pfp.png"):
    """Create a circular profile picture."""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors - warm gradient colors
    bg_color = (139, 92, 246)  # Purple
    bg_color2 = (59, 130, 246)  # Blue
    
    # Draw circular background with gradient effect
    center = size // 2
    radius = size // 2 - 10
    
    # Create gradient background
    for y in range(size):
        for x in range(size):
            # Check if pixel is within circle
            dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
            if dist <= radius:
                # Calculate gradient
                ratio = y / size
                r = int(bg_color[0] * (1 - ratio) + bg_color2[0] * ratio)
                g = int(bg_color[1] * (1 - ratio) + bg_color2[1] * ratio)
                b = int(bg_color[2] * (1 - ratio) + bg_color2[2] * ratio)
                img.putpixel((x, y), (r, g, b, 255))
    
    # Add text
    text = "K2.5"
    
    # Try to use a font, fall back to default
    try:
        # Try system fonts
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Windows/Fonts/arial.ttf",
        ]
        font = None
        for path in font_paths:
            if os.path.exists(path):
                font = ImageFont.truetype(path, size // 3)
                break
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10
    
    # Draw text with slight shadow
    shadow_color = (0, 0, 0, 128)
    draw.text((x + 3, y + 3), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG')
    print(f"Created profile picture: {output_path}")
    return output_path

if __name__ == "__main__":
    create_pfp()
