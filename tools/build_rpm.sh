#! /bin/sh

# Tell pbr to skip version auto-generation
export PBR_VERSION="2015.1"

if [ $# == 0 ]; then
    echo "Please provide project top dir:"
    read TOP_DIR
fi

TOP_DIR=${TOP_DIR:-$1}
TOOL_DIR=${TOP_DIR}/tools
RELEASE=`date "+%Y%m%d"`

cd ${TOP_DIR}

rm -rf ${TOP_DIR}/dist/
rm -rf ${TOP_DIR}/build/
rm -rf ${TOP_DIR}/nova_zvm_virt_driver.egg-info/

python setup.py bdist_rpm --release ${RELEASE} --post-install ${TOOL_DIR}/post_install --pre-uninstall ${TOOL_DIR}/pre_uninstall --post-uninstall ${TOOL_DIR}/post_uninstall
