# This script file was created by R. Treharne on 6/11/2024


# Load necessary libraries
library(png)
library(EBImage)

# Function to count the number of objects in an image
count_objects <- function(image_path, threshold = 0.5) {
  # Read the image
  img <- readPNG(image_path)
  
  # Convert the image to grayscale
  gray_img <- channel(img, "gray")
  
  # Apply thresholding to create a binary image
  binary_img <- gray_img > threshold
  
  # Find connected components
  cc <- bwlabel(binary_img)
  
  # Count the number of objects
  num_objects <- max(cc) - 1
  
  return(num_objects)
}