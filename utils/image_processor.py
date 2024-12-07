from PIL import Image, ImageFilter
import os

def optimize_background_image():
    # Path to your original image
    input_path = 'static/img/background/background.jpg'
    # Path for the optimized image
    output_path = 'static/img/background/auth-bg.jpg'
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Open and process image
    with Image.open(input_path) as img:
        # Apply slight blur
        img = img.filter(ImageFilter.GaussianBlur(radius=2))
        
        # Resize image while maintaining aspect ratio
        max_size = (1920, 1080)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save optimized image
        img.save(output_path, 'JPEG', 
                quality=85,  # Good quality while reducing file size
                optimize=True,
                progressive=True)

# Run the optimization
if __name__ == "__main__":
    optimize_background_image() 