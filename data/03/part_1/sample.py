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

def generate_files(filename, n):
    for i in range(100, 1000):
        df = sample_dataset(filename, n, i)
        fname = f"{filename.split('.')[0]}_{i}.csv"
        df.to_csv(fname, index=False)

if __name__ == "__main__":
    if len(sys.argv) == 3:
        filename = sys.argv[1]
        n = int(sys.argv[2])
        generate_files(filename, n)
    elif len(sys.argv) == 4:
        filename = sys.argv[1]
        n = int(sys.argv[2])
        output_filename = sys.argv[3]
        seed = int(Path(output_filename).stem.rsplit("_", 1)[-1])

        sampled_df = sample_dataset(filename, n, seed)
        sampled_df.to_csv(output_filename, index=False)
    else:
        print(
            "Usage: python sample.py <input_filename> <n> "
            "[<output_filename_with_seed>]"
        )
        sys.exit(1)
