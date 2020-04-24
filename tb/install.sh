#!/bin/env bash

set -eu

cd $(dirname $0)

SRC_DIR=$(pwd)
package=tb

if [ -z ${TARGET_DIR+x} ] ; then
	TARGET_DIR=$(echo $PATH | tr ":" "\n" | grep $HOME | head -n 1) 

	if [ `whoami` = "root" ] ; then
		TARGET_DIR=/usr/bin
	fi
fi

deps () {
    echo "Installing dependencies"

	if [ `whoami` = "root" ] ; then
		pip3 install -r ./requirements.txt
    else
        pip3 install --user -r ./requirements.txt
	fi
    
}

install () {
  	echo installing into $TARGET_DIR

	cd $TARGET_DIR

	cp $SRC_DIR/${package}.py ${package}

	chmod +x ${package}
}

uninstall () {
  	echo uninstalling from $TARGET_DIR
	cd $TARGET_DIR
 	unlink ${package} || rm -f ${package}
}


install_dev () {
    echo ""
    echo "Where should I put the symbolic link?"
    echo ""

    read -e -p "Enter path and press [ENTER]: " -i $TARGET_DIR TARGET_DIR
    cd $TARGET_DIR

    unlink  ${package} || rm -f ${package} || true

    ln -s ${SRC_DIR}/${package}.py ${package}
    cd -

}

test () {
	set -x
	echo $TARGET_DIR
	echo $SRC_DIR
}

"$@"