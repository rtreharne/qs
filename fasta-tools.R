# Define a function to extract sequences from a FASTA file
extract_sequences_from_fasta <- function(fasta_file) {
  
  # Read all lines from the specified FASTA file into a vector
  fasta_lines <- readLines(fasta_file)
  
  # Create an empty vector to store DNA sequences
  sequences <- c()
  
  # Loop through each line in the file
  for (line in fasta_lines) {
    # Check if the line does NOT start with '>', which marks header lines in FASTA format
    if (!startsWith(line, ">")) {
      # If it's a sequence line, add it to the 'sequences' vector
      sequences <- c(sequences, line)
    }
  }
  
  # Return the vector of sequences
  return(sequences)
}

# Define a function to count the occurrences of a motif in a sequence
count_motif <- function(sequence, motif="AAA") {
  
  # Initialise a counter variable to track motif occurrences
  count <- 0
  
  # Loop through the sequence in chunks matching the motif's length
  for (i in seq(1, nchar(sequence), by=nchar(motif))) {
    # Extract a substring (chunk) from the sequence starting at position 'i'
    chunk <- substr(sequence, i, i+nchar(motif)-1)
    # Compare the chunk to the motif; if they match, increment the counter
    if (motif == chunk) {
      count <- count + 1
    }
  }
  
  # Return the total count of motif occurrences
  return(count)
}

# Define a function to calculate the mean frequency of a motif across multiple sequences
calculate_mean_motif_freq <- function(sequences, motif = "AAA") {
  
  # Create an empty vector to store motif counts for each sequence
  motif_frequency <- c()
  
  # Loop through each sequence in the input list
  for (sequence in sequences) {
    # Use the 'count_motif' function to count occurrences of the motif in the current sequence
    count <- count_motif(sequence, motif)
    # Append the count to the 'motif_frequency' vector
    motif_frequency <- c(motif_frequency, count)
  }
  
  # Calculate and return the mean (average) motif frequency
  return(mean(motif_frequency))
}

# Define a function to compute the reverse complement of a DNA sequence
reverse_complement <- function(sequence) {
  # Create a named vector mapping each nucleotide to its complement
  complement_map <- c("A" = "T", "T" = "A", "C" = "G", "G" = "C")
  
  # Split the sequence into individual nucleotides (characters)
  nucleotides <- strsplit(sequence, split = "")[[1]]
  
  # Replace each nucleotide with its complement using the mapping vector
  complement <- complement_map[nucleotides]
  
  # Reverse the complemented sequence and join it back into a single string
  reverse_complement_sequence <- paste(rev(complement), collapse = "")
  
  # Return the reverse complement sequence
  return(reverse_complement_sequence)
}

# Define a function to find the most common triplet (3-nucleotide substring) in a sequence
find_most_common_triplet <- function(sequence) {
  # Check if the input sequence is long enough to contain at least one triplet
  if (nchar(sequence) < 3) {
    stop("Sequence must be at least 3 nucleotides long.") # Stop with an error message if too short
  }
  
  # Generate all triplets (3-character substrings) from the sequence
  triplets <- sapply(1:(nchar(sequence) - 2), function(i) {
    substr(sequence, i, i + 2) # Extract triplet starting at position 'i'
  })
  
  # Count the frequency of each unique triplet using the 'table' function
  triplet_counts <- table(triplets)
  
  # Identify the most common triplet(s) by finding the maximum count
  most_common <- names(triplet_counts[triplet_counts == max(triplet_counts)])
  
  # Return the most common triplet(s) as a vector
  return(most_common)
}
