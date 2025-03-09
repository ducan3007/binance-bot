from PIL import Image

def concatenate_images(image1_path, image2_path, output_path):
    try:
        # Open the two images
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)
        
        # Get dimensions of both images
        width1, height1 = img1.size
        width2, height2 = img2.size
        
        # Calculate the dimensions of the new image
        # Width will be sum of both widths
        # Height will be the maximum height of the two images
        new_width = width1 + width2
        new_height = max(height1, height2)
        
        # Create a new blank image with the calculated dimensions
        new_image = Image.new('RGB', (new_width, new_height))
        
        # Paste first image at position (0,0)
        new_image.paste(img1, (0, 0))
        
        # Paste second image right next to first image
        new_image.paste(img2, (width1, 0))
        
        # Save the concatenated image
        new_image.save(output_path)
        print(f"Images successfully concatenated and saved as {output_path}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

