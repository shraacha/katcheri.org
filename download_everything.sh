#!/bin/sh

download_output_dir='all_concerts'

usage() {
	cat << EOF
usage: $0 <aria_input_file> <working_dir> <max_DL_MiB/s>

where
  - aria_input_file is the *absolute* path to the full aria2c download list
  - working_dir is the *absolute* path to the working directory that contains
    the $download_output_dir/ directory
  - max_DL_MiB/s is your network's speed limitations in *Mebibytes per sec*

NOTE:
To get MiB/s speed limitations:
1. Go to https://fast.com and note down the mbps DL speed in mbps
2. Divide by 8, then round upwards to the nearest whole number
EOF
} >&2

# Assert that all arguments are passed
if [ "$#" -ne 3 ]; then
	echo "ERROR: all required arguments were not passed!" >&2
	usage
	exit 1
fi

aria_input_file="$1"
working_dir="$2"
max_dl="$3"

# Assert that aria_input_file exists and is a readable file
if [ ! -r "$aria_input_file" ]; then
	echo "ERROR: $aria_input_file is not a readable file!" >&2
	usage
	exit 1
fi

# Assert that working_dir contains the download output directory inside
if [ ! -d "$working_dir/$download_output_dir" ]; then
	echo "ERROR: $working_dir/$download_output_dir is not a valid directory!" >&2
	usage
	exit 1
fi

cd "$working_dir" || exit 1
aria2c \
	--http-accept-gzip true \
	--optimize-concurrent-downloads true \
	--max-concurrent-downloads=100 \
	--max-overall-download-limit="${max_dl}M" \
	--input-file="$aria_input_file"
