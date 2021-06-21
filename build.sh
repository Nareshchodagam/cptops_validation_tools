#!/bin/bash

###########################################################
# build.sh
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
#
###########################################################

# os/env setup should be done in package, don't think we need this here
# cd "$( dirname "${BASH_SOURCE[0]}" )"
set -e

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
  echo "-v version is a required argument"
  exit 1
fi


echo "----- Start CPT Tools TnRP build script -----"
HERE=$(pwd)
echo "pwd: $HERE"

echo "----- cloning required repos -----"
git clone git@git.soma.salesforce.com:CPT/cptops_idbhost.git $HERE/cptops_idbhost -b master
git clone git@git.soma.salesforce.com:CPT/cptops_nagios.git $HERE/cptops_nagios -b master
git clone git@git.soma.salesforce.com:CPT/cptops_gus_base.git $HERE/cptops_gus_base -b master
git clone git@git.soma.salesforce.com:CPT/decomm.git $HERE/decomm -b master
git clone git@git.soma.salesforce.com:CPT/cptops_sysfiles.git $HERE/sysfiles -b master
git clone git@git.soma.salesforce.com:CPT/cptops_exec_with_creds.git $HERE/cptops_exec_with_creds -b master
git clone git@git.soma.salesforce.com:CPT/cptops_core.git $HERE/core -b master
git clone git@git.soma.salesforce.com:ssa/ssa_service_validation.git $HERE/ssa -b master
git clone git@git.soma.salesforce.com:SystemsSecurity/sec_patch.git $HERE/sec_patch -b master
git clone git@git.soma.salesforce.com:puppet/coresystem.git $HERE/coresystem -b master

yum install -y python-setuptools

echo "----- packaging the rpm with fpm -----"
fpm -s python -t rpm \
	-v $version --iteration "$iteration" \
	--architecture noarch \
	--verbose \
	--exclude 'usr' \
	-n cpt-tools \
	--rpm-defattrfile 755 \
	setup.py

echo "----- End CPT Tools TnRP build script -----"

echo "dummy commit "
echo "dummy commit 21_05"
