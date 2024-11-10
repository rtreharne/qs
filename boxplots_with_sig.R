# Load the data
url <- "https://raw.githubusercontent.com/rtreharne/qs/main/data/02/zebrafish_105.csv"
zebrafish_data <- read.csv(url)

# Convert the grouping variable to a factor
zebrafish_data$conc_pc <- as.factor(zebrafish_data$conc_pc)

# Perform ANOVA
zebrafish_aov <- aov(length_micron ~ conc_pc, data = zebrafish_data)

# Perform Tukey HSD test
tukey_result <- TukeyHSD(zebrafish_aov)

# Extract Tukey results
tukey_df <- as.data.frame(tukey_result$conc_pc)
tukey_df$comparison <- rownames(tukey_df)

# Add significance labels based on p-values
tukey_df$significance <- ifelse(tukey_df$`p adj` < 0.001, "***",
                                ifelse(tukey_df$`p adj` < 0.01, "**",
                                       ifelse(tukey_df$`p adj` < 0.05, "*", "")))

# Filter only significant comparisons
significant_comparisons <- tukey_df[tukey_df$significance != "", ]

# Create the boxplot
boxplot(length_micron ~ conc_pc, data = zebrafish_data,
        xlab = "Alcohol Conc. (%)", ylab = "Embryo Length (microns)",
        col = "lightblue", main = "",
        ylim = c(1500, 3500))

# Add significance annotations (brackets)
y_max <- 3000  # You can adjust this based on the actual data or leave it like this
offset <- 0.05 * y_max  # Adjust for the spacing between brackets

# Loop through the significant comparisons and add brackets
for (i in 1:nrow(significant_comparisons)) {
  # Get the groups being compared
  groups <- unlist(strsplit(significant_comparisons$comparison[i], "-"))
  group1 <- as.character(groups[1]) 
  group2 <- as.character(groups[2]) 
  label <- significant_comparisons$significance[i]
  
  # Get the x-axis positions of the groups
  group1_x <- which(levels(zebrafish_data$conc_pc) == group1)
  group2_x <- which(levels(zebrafish_data$conc_pc) == group2)
  
  # Calculate the position for the bracket
  y_position <- y_max + (i * offset)
  
  # Draw the bracket connecting the two groups
  segments(group1_x, y_position, group2_x, y_position, lwd = 1)
  segments(group1_x, y_position, group1_x, y_position - offset * 0.5)
  segments(group2_x, y_position, group2_x, y_position - offset * 0.5)
  
  # Add the significance label above the bracket
  text(x = mean(c(group1_x, group2_x)), y = y_position + offset * 0.3, labels = label)
}

