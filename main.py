import web
import subprocess
import time
import config

urls = (
    '/menu', 'Menu',
    '/create/(.*)/(.*)', 'Create',
    '/delete_menu', 'DeleteMenu',
    '/snapshot_menu', 'SnapshotMenu',
    '/delete/(.*)', 'Delete',
    '/boot/(.*)/(.*)', 'Boot',
    '/clone_boot/(.*)/(.*)', 'CloneBoot',
    '/snapshot/(.*)', 'Snapshot'
)
t_globals = dict(
    datestr=web.datestr,
)
render = web.template.render('templates/', globals=t_globals)
app = web.application(urls, globals())


class Dataset:
    parent_name = ""
    name = ""
    boot = ""
    snapshot = 0
    origin = ""

    def __init__(self):
        pass


def sanboot_dataset_list(boot_type):
    result = subprocess.check_output(["zfs", "get", "-t volume", "com.qnap:sanboot", ])
    dataset_list = dict()
    for line in result.splitlines()[1:]:
        item = line.split()
        ds = Dataset()
        name = item[0]
        ds.boot = item[2]
        try:
            ds.parent_name = name[:name.rindex("/")]
            ds.name = name[name.rindex("/") + 1:]
            if ds.boot == boot_type:
                dataset_list[ds.name] = ds

        except:
            pass

    result = subprocess.check_output(["zfs", "get", "-t snapshot", "com.qnap:sanboot", ])
    for line in result.splitlines()[1:]:
        item = line.split()
        name = item[0]
        dsname = name[:name.rindex("@")]
        snapname = name[name.rindex("@") + 1:]
        if snapname == 'init' and item[2] == boot_type:
            if dsname[dsname.rindex("/") + 1:] in dataset_list:
                dataset_list[dsname[dsname.rindex("/") + 1:]].snapshot = 1

    return dataset_list

def sanboot_children_list(volname):
    result = subprocess.check_output(["zfs", "get", "-t volume", "origin", ])
    dataset_list = dict()
    for line in result.splitlines()[1:]:
        item = line.split()
        name = item[0]
        origin = item[2]
        try:

            if origin == volname+"@init":
                ds = Dataset()
                ds.parent_name = name[:name.rindex("/")]
                ds.name = name[name.rindex("/") + 1:]
                ds.origin = origin
                dataset_list[ds.name] = ds

        except:
            pass

    return dataset_list

def reload_ctld():
    ctld_org_conf = open("/etc/ctl.bsd.conf", "r")
    ctld_conf = open("/etc/ctl.conf", "w")
    org_conf = ctld_org_conf.read()
    for k, ds in sanboot_dataset_list("on").items():
        org_conf = org_conf + "target iqn.2014-04.com.qnap:{0} {{\n" \
                              "  auth-group no-authentication\n" \
                              "  portal-group pg0\n" \
                              "    lun 0 {{\n" \
                              "      path /dev/zvol/{1}{0}\n" \
                              "    }}\n" \
                              "}} ".format(ds.name, config.zfsroot) + "\n"
    for k, ds in sanboot_dataset_list("clone").items():
        org_conf = org_conf + "target iqn.2014-04.com.qnap:{0} {{\n" \
                              "  auth-group no-authentication\n" \
                              "  portal-group pg0\n" \
                              "    lun 0 {{\n" \
                              "      path /dev/zvol/{1}{0}\n" \
                              "    }}\n" \
                              "}} ".format(ds.name, config.zfsroot) + "\n"
    ctld_conf.write(org_conf)
    ctld_conf.close()
    ctld_org_conf.close()
    subprocess.check_output(["/etc/rc.d/ctld", "reload", ])


def create_zvol(volname, volsize):

    try:
        subprocess.check_output(
            ["zfs", "create", "-V", volsize, "-s", "-o", "com.qnap:sanboot=on", config.zfsroot + volname, ])
        reload_ctld()
    except:
        pass


def clone_zvol(volname, mac):

    try:
        subprocess.check_output(
            ["zfs", "clone", "-o", "com.qnap:sanboot=clone", config.zfsroot + volname + "@init",
             config.zfsroot + volname + "-" + mac])
        subprocess.check_output(
            ["zfs", "snapshot", config.zfsroot + volname + "-" + mac+"@init"])
    except:
        pass


def snapshot_zvol(volname):

    try:
        subprocess.check_output(["zfs", "snapshot", config.zfsroot + volname + "@" + "init", ])
    except:
        pass


def delete_zvol(volname):

    try:
        subprocess.check_output(["zfs", "set", "com.qnap:sanboot=off", config.zfsroot + volname, ])
        for k,v in sanboot_children_list("zdisk0/fedora").items():
            subprocess.check_output(["zfs", "set", "com.qnap:sanboot=off", config.zfsroot + k, ])
        reload_ctld()
        time.sleep(1)  # XXX
        subprocess.check_output(["zfs", "destroy", "-R", config.zfsroot + volname, ])
    except:
        pass


# noinspection PyClassHasNoInit
class Menu:

    def GET(self):
        reload_ctld()
        return render.menu(sanboot_dataset_list("on"), config.sanboot_ip)


# noinspection PyClassHasNoInit
class CloneBoot:

    def GET(self, volname, mac):
        clone_zvol(volname, mac)
        time.sleep(1)  # XXX
        reload_ctld()
        time.sleep(1)  # XXX
        return render.clone_boot(volname + "-" + mac, config.sanboot_ip)


# noinspection PyClassHasNoInit
class Boot:

    def GET(self, volname, mac):
        dataset_list = sanboot_dataset_list("on")
        if volname in dataset_list and dataset_list[volname].snapshot == 1:
            return render.boot(volname, mac, config.sanboot_ip)
        return render.boot(volname, "", config.sanboot_ip)


# noinspection PyClassHasNoInit
class Create:

    def GET(self, volname, volsize):
        create_zvol(volname, volsize)
        return "#!ipxe\nchain http://{0}:8080/menu".format(config.sanboot_ip)


# noinspection PyClassHasNoInit
class Delete:

    def GET(self, volname):
        delete_zvol(volname)
        return "#!ipxe\nchain http://{0}:8080/menu".format(config.sanboot_ip)


# noinspection PyClassHasNoInit
class DeleteMenu:

    def GET(self):
        return render.delete(sanboot_dataset_list("on"), config.sanboot_ip)


# noinspection PyClassHasNoInit
class Snapshot:

    def GET(self, volname):
        snapshot_zvol(volname)
        return "#!ipxe\nchain http://{0}:8080/menu".format(config.sanboot_ip)


# noinspection PyClassHasNoInit
class SnapshotMenu:

    def GET(self):
        return render.snapshot(sanboot_dataset_list("on"), config.sanboot_ip)


if __name__ == "__main__":
    app.run()
