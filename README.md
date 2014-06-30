zanboot
=======

sanboot based on zfs

First of all, you need FreeBSD-10. I use native iscsi-target server in FreeBSD-10. 
But ZFS in FreeBSD-10 has bug on create clone(r264729), you need the patch this first.

And then, you should create a file named /etc/ctl.bsd.conf:
=========
portal-group pg0 {
        discovery-auth-group no-authentication
        listen 0.0.0.0
        listen [::]
}
=========
This is a base file of /etc/ctl.conf, zanboot will merge this config with new iSCSI target.


You should also edit config.py, zfsroot is your dataset name which you want to store lun image.
sanboot_ip is you server's ip. After web.py runs, http://${sanboot_ip}:8080/menu will be used.
Please redirect your iPXE to this url.



Appendix.

volume clone patch:
http://svnweb.freebsd.org/base?view=revision&revision=264729

