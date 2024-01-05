#!/bin/bash

# Define the list of batches
batches=("_batch001_mini" "_batch002_mini" "_batch003_mini") # Add your batch names here

# Get the current username
current_user=$(whoami)

# Loop over each batch
for batch in "${batches[@]}"; do
    start_time=$(date +%s)  # Capture the start time
    echo "Processing $batch..."

    # Run the Python script for the current batch
    sudo venv/bin/python extract_files_from_bids.py --batch "$batch" --path_save data/"$batch".h5 

    # Check if the Python script execution was successful
    if [ $? -eq 0 ]; then
        # Change ownership of the .h5 file to the current user
        sudo chown "$current_user" "data/${batch}.h5"
        sudo chmod 777 "data/${batch}.h5"
        # Upload the .h5 file to Dropbox
        rclone copy "data/${batch}.h5" dropbox_moritz:Sauron/data/ --progress

        # Check if the upload was successful
        if [ $? -eq 0 ]; then
            echo "Upload successful. Deleting local file..."
            # Delete the local .h5 file
            sudo rm -f "data/${batch}.h5"
        else
            echo "Error: Failed to upload ${batch}.h5 to Dropbox."
        fi
    else
        echo "Error: Failed to process $batch."
    fi
    end_time=$(date +%s) # Capture end time of the loop iteration
    duration=$((end_time - start_time)) # Calculate the duration
    echo "Duration for $batch: $duration seconds"
done

echo "All batches processed."
