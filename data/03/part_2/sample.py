import pandas as pd
import sys
from pathlib import Path

def sample_dataset(filename, n, seed):
    # Ensure the seed has either 3 or 9 digits
    if not (100 <= seed <= 999 or 100000000 <= seed <= 999999999):
        raise ValueError("Seed must be a 3-digit or 9-digit integer.")
    
    # Load the dataset
    df = pd.read_csv(filename)
    
    # Sample the dataset
    sampled_df = df.sample(n=n, random_state=seed)
    
    return sampled_df

def generate_files(filename, n=100, output_filename=None):
    if output_filename is None:
        output_filename = Path(filename).stem

    for i in range(100, 1000):
        df = sample_dataset(filename, n, i)
        fname = f"{output_filename}_{i}.csv"
        df.to_csv(fname, index=False)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        generate_files(sys.argv[1])
    elif len(sys.argv) == 5:
        filename = sys.argv[1]
        n = int(sys.argv[2])
        seed = int(sys.argv[3])
        output_filename = sys.argv[4]

        sampled_df = sample_dataset(filename, n, seed)
        sampled_df.to_csv(output_filename, index=False)
    else:
        print(
            "Usage: python sample.py <input_filename> "
            "[<n> <seed> <output_filename>]"
        )
        sys.exit(1)
