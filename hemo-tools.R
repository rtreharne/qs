# This script file was created by R. Treharne on 6/11/2024

# Load necessary libraries
library(png)
library(EBImage)

# Function to count the number of objects in an image
count_viable <- function(image_path, threshold = 0.5) {
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

count_nonviable <- function(image_path, blue_threshold = 0.5) {
  # Read the image
  img <- readPNG(image_path)
  
  # Split the image into R, G, B channels
  red_channel <- img[,,1]
  green_channel <- img[,,2]
  blue_channel <- img[,,3]
  
  # Create a binary mask for blue regions
  # Only pixels where the blue channel is strong and dominates red and green will be counted
  blue_mask <- (blue_channel > blue_threshold) & (blue_channel > red_channel) & (blue_channel > green_channel)
  
  # Find connected components in the blue mask
  cc <- bwlabel(blue_mask)
  
  # Count the number of blue objects
  num_blue_objects <- max(cc)
  
  return(num_blue_objects)
}

proportion_nonviable <- function(image_path) {
  viable <- count_viable(image_path)
  nonviable <- count_nonviable(image_path)
  return(nonviable * 100 / (viable + nonviable))
}