"""
Image watermarking utility
Adds store name watermark to product images
"""
import os
from PIL import Image, ImageDraw, ImageFont
from config import app_config

async def add_watermark(image_path: str, store_name: str, output_path: str = None) -> str:
    """
    Add watermark to image with store name
    Preserves original image quality and format.
    
    Args:
        image_path: Path to original image
        store_name: Store name to use as watermark
        output_path: Optional output path, defaults to same as input
    
    Returns:
        Path to watermarked image
    """
    img = None
    image = None
    txt_layer = None
    watermarked = None
    
    try:
        # Open image
        img = Image.open(image_path)
        img.load()  # Load image data to handle potential truncation
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            image = img.convert('RGBA')
        else:
            image = img.copy()
        
        if image is None:
            raise ValueError("Failed to load or convert image")
        
        # Create transparent overlay
        txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        # Calculate font size based on image width
        img_width, img_height = image.size
        # Base size as a fraction of width
        base_size = int(img_width * 0.04)
        # Clamp font size so it doesn't look too big or too small
        min_size = app_config.WATERMARK_FONT_SIZE
        max_size = int(img_width * 0.07)
        font_size = max(min_size, min(base_size, max_size))
        
        # Try to load a font, fallback to default
        try:
            # Try common system fonts
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "C:\\Windows\\Fonts\\arial.ttf"
            ]
            
            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Prepare watermark text
        watermark_text = f"{store_name} x @ethiostorebot"
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position watermark at bottom-right with padding
        padding = 20
        x = img_width - text_width - padding
        y = img_height - text_height - padding
        
        # Draw semi-transparent background rectangle
        bg_padding = 10
        draw.rectangle(
            [x - bg_padding, y - bg_padding, 
             x + text_width + bg_padding, y + text_height + bg_padding],
            fill=(0, 0, 0, 120)
        )
        
        # Draw watermark text
        draw.text(
            (x, y),
            watermark_text,
            font=font,
            fill=(255, 255, 255, app_config.WATERMARK_OPACITY)
        )
        
        # Composite the watermark onto the original image
        watermarked = Image.alpha_composite(image, txt_layer)
        
        # Determine original format and extension
        original_format = img.format
        if output_path is None:
            output_path = image_path
        else:
            # Preserve original extension if not specified
            original_ext = os.path.splitext(image_path)[1].lower()
            output_ext = os.path.splitext(output_path)[1].lower()
            if not output_ext:
                output_path = output_path + original_ext
        
        # Save watermarked image preserving original format and quality
        if original_format in ['JPEG', 'JPG'] or os.path.splitext(output_path)[1].lower() in ['.jpg', '.jpeg']:
            # For JPEG, convert to RGB and save with high quality
            watermarked = watermarked.convert('RGB')
            watermarked.save(output_path, quality=95, optimize=False)
        elif original_format == 'PNG' or os.path.splitext(output_path)[1].lower() == '.png':
            # For PNG, preserve transparency
            watermarked.save(output_path, optimize=False)
        elif original_format == 'WEBP' or os.path.splitext(output_path)[1].lower() == '.webp':
            # For WebP, convert to RGB if needed and save with high quality
            if watermarked.mode == 'RGBA':
                # WebP supports transparency, but we'll convert to RGB for compatibility
                watermarked = watermarked.convert('RGB')
            watermarked.save(output_path, quality=95, optimize=False)
        else:
            # Fallback: convert to RGB and save as JPEG
            watermarked = watermarked.convert('RGB')
            output_path = os.path.splitext(output_path)[0] + '.jpg'
            watermarked.save(output_path, quality=95, optimize=False)
        
        return output_path
    
    except Exception as e:
        print(f"Error adding watermark to {image_path}: {e}")
        # If watermarking fails, just return original path
        return image_path
    finally:
        # Ensure all image objects are closed
        if img is not None:
            img.close()
        if image is not None:
            image.close()
        if txt_layer is not None:
            txt_layer.close()
        if watermarked is not None:
            watermarked.close()

def create_thumbnail(image_path: str, max_size: tuple = (800, 800)) -> str:
    """
    Create thumbnail of image for faster loading
    
    Args:
        image_path: Path to image
        max_size: Maximum dimensions (width, height)
    
    Returns:
        Path to thumbnail
    """
    try:
        image = Image.open(image_path)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save thumbnail
        thumb_path = image_path.replace('.', '_thumb.')
        image.save(thumb_path, quality=85, optimize=True)
        
        return thumb_path
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return image_path



