import pandas as pd
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
import joblib
import tkinter as tk
from tkinter import messagebox

# adding this to get the parent directory.
from pathlib import Path
DIR = Path(__file__).resolve().parent

# Load CSV
csv_path = str(DIR / "csv files/head_pose.csv")
data = pd.read_csv(csv_path)

X = data[["Roll", "Pitch", "Yaw"]]
y = data["Label"]

num_rows = len(y)

# Normalize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train SVM
svm = SVC(kernel="rbf")
svm.fit(X_scaled, y)

# Save model and scaler
joblib.dump(svm, str(DIR.parent / "Models/3featuresSVM/svm_model.pkl"))
joblib.dump(scaler, str(DIR.parent / "Models/3featuresSVM/scaler.pkl"))

root = tk.Tk()
root.withdraw()  # hide the main window

# Show a message box
messagebox.showinfo("Notice", f"SVM training completed on {num_rows} images data")

# After clicking OK, the dialog disappears automatically
root.destroy()
print("Step 2 complete: SVM trained and saved.")
