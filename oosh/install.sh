#!/usr/bin/env bash

set -eu

package=oosh

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

echo "Installation successful"
