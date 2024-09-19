import pandas as pd
import sys

def sample_dataset(filename, n, seed):
    # Ensure the seed is a 3-digit integer
    if not (100 <= seed <= 999):
        raise ValueError("Seed must be a 3-digit integer (100-999).")
    
    # Load the dataset
    df = pd.read_csv(filename)
    
    # Sample the dataset
    sampled_df = df.sample(n=n, random_state=seed)
    
    return sampled_df

def generate_files(filename, n):
    for i in range(100, 1000):
        df = sample_dataset(filename, n, i)
        fname = f"{filename.split('.')[0]}_{i}.csv"
        df.to_csv(fname, index=False)

if __name__ == "__main__":
    # Check if the correct number of arguments is provided
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <filename> <n>")
        sys.exit(1)

    # Parse arguments
    filename = sys.argv[1]
    n = int(sys.argv[2])
    
    # Generate files
    generate_files(filename, n)
