"""
Telegram Image Helper
--------------------
Utilities for optimizing images for Telegram
"""

import io
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

def optimize_image_for_telegram(image_data: bytes, max_size: int = 1024 * 1024) -> bytes:
    """
    Optimize an image to ensure it's compatible with Telegram.
    Telegram has specific requirements for images, especially for photo messages.
    
    Args:
        image_data: The original image data as bytes
        max_size: Maximum size in bytes (1MB default, Telegram limit is 10MB)
        
    Returns:
        Optimized image data as bytes
    """
    try:
        # First try to identify the image format
        print(f"Optimizing image of size: {len(image_data)} bytes")
        
        # Create a BytesIO object from the image data
        input_buffer = io.BytesIO(image_data)
        input_buffer.seek(0)
        
        try:
            # Try to open the image
            img = Image.open(input_buffer)
            print(f"Image format: {img.format}, Mode: {img.mode}, Size: {img.size}")
        except Exception as e:
            print(f"Error opening image: {e}")
            # If we can't open it, return the original data
            return image_data
        
        # Check if the image needs to be converted to RGB
        if img.mode == 'RGBA':
            print("Converting RGBA to RGB")
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            # Paste the image on the background using alpha as mask
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            print(f"Converting {img.mode} to RGB")
            img = img.convert('RGB')
        
        # Start with high quality
        quality = 95
        output = io.BytesIO()
        
        # Save with initial quality
        img.save(output, format='JPEG', quality=quality)
        current_size = output.tell()
        print(f"Initial JPEG size: {current_size} bytes")
        
        # If the image is too large, reduce quality until it's small enough
        while current_size > max_size and quality > 30:
            output = io.BytesIO()
            quality -= 5
            print(f"Reducing quality to {quality}")
            img.save(output, format='JPEG', quality=quality)
            current_size = output.tell()
            print(f"New size: {current_size} bytes")
        
        # If reducing quality isn't enough, also resize the image
        scale_factor = 1.0
        while current_size > max_size and scale_factor > 0.3:
            scale_factor -= 0.1
            new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
            print(f"Resizing to {new_size} (scale: {scale_factor:.2f})")
            resized_img = img.resize(new_size, Image.LANCZOS)
            
            output = io.BytesIO()
            resized_img.save(output, format='JPEG', quality=quality)
            current_size = output.tell()
            print(f"New size after resize: {current_size} bytes")
        
        # Get the final optimized image data
        output.seek(0)
        final_data = output.getvalue()
        print(f"Final image size: {len(final_data)} bytes")
        return final_data
        
    except Exception as e:
        print(f"Error optimizing image: {e}")
        # If optimization fails, return the original data
        return image_data

def create_token_visualization_image(token_name: str, token_symbol: str, address: str, width: int = 600, height: int = 400) -> bytes:
    """
    Create a nice-looking visualization image for a token
    
    Args:
        token_name: The name of the token
        token_symbol: The token symbol
        address: The token address
        width: Image width
        height: Image height
        
    Returns:
        Image data as bytes
    """
    try:
        # Create a new image with a gradient background
        img = Image.new('RGB', (width, height), color=(66, 135, 245))
        draw = ImageDraw.Draw(img)
        
        # Try to load a nice font, fall back to default if unavailable
        try:
            # For MacOS/Linux systems
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        except:
            try:
                # For Windows systems
                title_font = ImageFont.truetype("arial.ttf", 36)
                body_font = ImageFont.truetype("arial.ttf", 24)
                small_font = ImageFont.truetype("arial.ttf", 16)
            except:
                # Default fallback
                title_font = ImageFont.load_default()
                body_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
        
        # Draw title
        draw.text((width//2, height//3), "Bubblemaps Visualization", 
                 fill=(255, 255, 255), font=title_font, anchor="mm")
        
        # Draw token info
        if token_name and token_symbol:
            draw.text((width//2, height//2), f"{token_name} ({token_symbol})", 
                     fill=(255, 255, 255), font=body_font, anchor="mm")
        elif token_name:
            draw.text((width//2, height//2), token_name, 
                     fill=(255, 255, 255), font=body_font, anchor="mm")
        
        # Draw address
        short_address = f"{address[:10]}...{address[-8:]}"
        draw.text((width//2, height//2 + 40), short_address, 
                 fill=(220, 220, 220), font=small_font, anchor="mm")
        
        # Draw footer
        draw.text((width//2, height - 30), "Loading visualization failed - check online map", 
                 fill=(200, 200, 200), font=small_font, anchor="mm")
        
        # Convert to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=90)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error creating token visualization: {e}")
        # Create a simple fallback image
        img = Image.new('RGB', (width, height), color=(100, 149, 237))
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        return output.getvalue() 