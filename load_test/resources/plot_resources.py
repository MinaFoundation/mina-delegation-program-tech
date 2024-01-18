import pandas as pd
import matplotlib.pyplot as plt
import sys

# Check if an input file was provided as an argument
if len(sys.argv) != 2:
    print("Usage: python plot_resources.py input_file")
    sys.exit(1)

input_file = sys.argv[1]

data = pd.read_csv(input_file, delim_whitespace=True)

data["Time"] = pd.to_datetime(data["Time"], format="%H:%M:%S")

data["MEM(MB)"] = data["MEM(MB)"].str.replace(",", ".").astype(float)

# Plotting CPU Usage
plt.figure(figsize=(10, 5))
plt.plot(data["Time"], data["%CPU"], label="CPU Usage (%)", color="r", marker="o")

# Plotting Memory Usage
plt.plot(
    data["Time"], data["MEM(MB)"], label="Memory Usage (MB)", color="b", marker="o"
)

# Adding title and labels
plt.title("CPU and Memory Usage Over Time")
plt.xlabel("Time")
plt.ylabel("Usage")

plt.legend()

# Rotate date labels for better readability
plt.xticks(rotation=45)

# Saving the plot to an image file
plt.tight_layout()
output_image_file = input_file.replace(".txt", ".png")  # Change extension to .png
plt.savefig(output_image_file)
print(f"Plot saved to {output_image_file}")
