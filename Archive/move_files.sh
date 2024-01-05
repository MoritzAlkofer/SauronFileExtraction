# Load EEG files from external file
eeg_files_list="eeg_files.txt"
mapfile -t eeg_files < "$eeg_files_list"

# Define paths  
src_path="bdsp/opendata/EEG/data"
dest_path="dropbox-moritz:/Datasets/zz_EEGs_BDSP_BIDS"

# Counter 
count=1

# Copy files
for file in "${eeg_files[@]}"
do  
  echo "Copying file $count"

  rclone copy "$file" "$dest_path"

  count=$((count + 1)) 
done