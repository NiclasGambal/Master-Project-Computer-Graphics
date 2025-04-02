import os
import cv2
import numpy as np
import glob

"""
Script Name: combine_results.py
Description: Combines individual rendered radiography layers by computing cumulative transmission,
             and creates a final composite image.
Usage: Run this script after rendering individual layers.
"""

# --------------------------------------------------
# User Adjustable Parameters
# --------------------------------------------------

# Set the fixed input/output directory. 
# The input directory must match the output directory of render.py.
INPUT_DIR = "/approach_1_results/"
OUTPUT_FILENAME = "approach_1_final_result.png"

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def srgb_to_linear(img, gamma=2.2):
    return np.power(np.clip(img, 0, 1), gamma)

def linear_to_srgb(img, gamma=2.2):
    return np.power(np.clip(img, 0, 1), 1.0 / gamma)

# --------------------------------------------------
# Main Execution
# --------------------------------------------------
output_path = os.path.join(INPUT_DIR, OUTPUT_FILENAME)
image_files = sorted([f for f in glob.glob(os.path.join(INPUT_DIR, "*.png"))
                       if not f.endswith(OUTPUT_FILENAME)])

combined_transmission = None

for img_path in image_files:
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
    img_linear = srgb_to_linear(img)
    transmission = 1.0 - img_linear
    if combined_transmission is None:
        combined_transmission = np.ones_like(transmission)
    combined_transmission *= transmission

composite_linear = 1.0 - combined_transmission
composite_srgb = linear_to_srgb(composite_linear)
final_image = np.clip(composite_srgb * 255.0, 0, 255).astype(np.uint8)
cv2.imwrite(output_path, final_image)
print("Final radiography result of the first approach created at:", output_path)
