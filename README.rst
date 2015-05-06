==============
networking-zvm
==============

This project implements zVM ML2 Mechanism Driver and Neutron zvm agent,
integrate zVM networking with OpenStack Neutron.


How to Install
--------------

Run the following command to install neutron zvm agent in the system:

::

    $ python setup.py install


Configuration
-------------

This section describes configuration settings related to Neutron zvm plugin.

In neutron.conf, set:

::

    [DEFAULT]
    base_mac = <zvm-base_mac>
    core_plugin = ml2

In addition, in ml2_conf.ini:

::

    [ml2]
    mechanism_drivers = zvm
    type_drivers = ml2
    tenant_network_types = local,flat,vlan
    [ml2_type_flat]
    flat_networks = <vswitch-name-list>

Finally, in neutron_zvm_plugin.ini:

::

    [AGENT]
    zvm_host = <zvm-compute-host-name>
    zvm_xcat_server = <xcat-server-ip-addr>
    zvm_xcat_username = <xcat-admin-username>
    zvm_xcat_password = <xcat-admin-password>

Where:

<zvm-base-mac>: Base MAC address that is used to generate MAC for virtual
interfaces specified as 6 pairs of hexadecimal digits separated by colons
(for example, 02:00:00:EE:00:00). The first three pairs of hexadecimal digits
should be the same as USERPREFIX in the VMLAN statement in the z/VM SYSTEM
CONFIG file. You can modify the fourth pair to any range, as appropriate to
your system. The final two pairs of hexadecimal digits for the MAC address
should be 00 and will be replaced with generated values.

<vswitch-name-list>: List of z/VM vswitch names with which flat networks can be
created.

<zvm-compute-host-name>: Same value as specified for the host property in
nova.conf. This is a unique identifier of the compute node.

<xcat-server-ip-addr>: The xCAT MN IP address or host name.

<xcat-admin-username>: The user name of the xCAT REST (Representational State
Transfer) API user.

<xcat-admin-password>: The password of the xCAT REST (Representational State
Transfer) API user.


References
----------

zVM: http://www.vm.ibm.com/
zVM networking: http://www.vm.ibm.com/networking/
