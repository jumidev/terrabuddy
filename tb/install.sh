#!/usr/bin/env bash

set -eu

package=tb

cd "$(dirname $0)"
chmod +x ${package}.py

echo "Installing dependencies"

pip3 install --user -r ./requirements.txt
dir=$(pwd)

echo ""
echo "Where should I put the symbolic link?"
echo ""

read -e -p "Enter path and press [ENTER]: " -i ~/bin lsdir
cd $lsdir

unlink  ${package} || true

ln -s ${dir}/${package}.py ${package}
cd -

echo "Installation successful, if you want to enable the handy shell aliases, add this line to your ~/.bashrc:"
echo 'eval $(tb --shell-aliases)'
