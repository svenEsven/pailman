#!/usr/local/bin/bash
# This file contains the install script for KMS

#init jail
initblueprint "$1"

# Initialise defaults

iocage exec "$1" svn checkout https://github.com/SystemRage/py-kms/trunk/py-kms /usr/local/share/py-kms
iocage exec "$1" "pw user add kms -c kms -u 666 -d /nonexistent -s /usr/bin/nologin"
iocage exec "$1" chown -R kms:kms /usr/local/share/py-kms /config
iocage exec "$1" mkdir /usr/local/etc/rc.d
cp "${includes_dir}"/py_kms.rc /mnt/"${global_dataset_iocage}"/jails/"$1"/root/usr/local/etc/rc.d/py_kms
iocage exec "$1" chmod u+x /usr/local/etc/rc.d/py_kms
iocage exec "$1" sysrc "py_kms_enable=YES"
iocage exec "$1" service py_kms start

exitblueprint "$1" "KMS is now accessible at ${ip4_addr%/*}:1688"
