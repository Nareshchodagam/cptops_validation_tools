#!/bin/bash
###########################################################
# build-rpm.sh
# uses fpm - a packaging tool, to wrap up all files in this repo into an rpm
# takes -i iteration
#       -v version
#
# ********** Example command for fpm ********************
# fpm -f -s dir -t rpm --rpm-os linux \
# --prefix <directory to be packaged> --version <version number> \
#  --name <rpm name> --architecture <architecture type - noarch,x86_64,etc.> \
# --exclude <exclude files> <directory where the rpm needs to be created>
# ************* A closer look at the "directory where the rpm needs to be created" that gets passed to the fpm command *****************
# You can specify the dir name directly or it can come from setup.py 
# ************** setup.py - a closer look ********************
# Doc reference : https://docs.python.org/2/distutils/setupscript.html
# For TnRP reference, use https://git.soma.salesforce.com/pipeline/release_pipeline/blob/master/pipeline_config_generator/setup.py
# You can specify the files to be packaged through 'packages=find_packages(<files to be packaged>)' 
# You can specify the files to be installed from the package through 'data_files=[ (<destination of the file>, ['file source'])]'

###########################################################
cd "$( dirname "${BASH_SOURCE[0]}" )"

iteration='1'
while getopts "i:v:h" opt; do
  case $opt in
    i)
      iteration=$OPTARG
      ;;
    v)
      version=$OPTARG
      ;;
    h)
      echo "Usage: $0 [-i <iteration number> -v <version number>]"
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      ;;
  esac
done

if [ -z "$iteration" ]
then
  echo "-i iteration is a required argument"
  exit 1
fi

if [ -z "$version" ]
then
  echo "-v version  is a required argument"
  exit 1
fi
fpm -s python -t rpm \
	-v $version --iteration "$iteration" \
	--architecture all \
	-n cpt-tools \
	--rpm-defattrfile 755 \
	setup.py