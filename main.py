import web, subprocess, os, time

urls = (
    '/menu', 'menu',
    '/create/(.*)/(.*)', 'create',
    '/delete_menu', 'delete_menu',
    '/snapshot_menu', 'snapshot_menu',
    '/delete/(.*)', 'delete',
    '/boot/(.*)/(.*)', 'boot',
    '/clone_boot/(.*)/(.*)', 'clone_boot',
    '/snapshot/(.*)', 'snapshot'
)
t_globals = dict(
  datestr=web.datestr,
)
render = web.template.render('templates/', 
    globals=t_globals)
render._keywords['globals']['render'] = render
app = web.application(urls, globals())

class dataset:
	parent_name = ""
	name = ""
	boot = ""
	snapshot = 0

def sanboot_dataset_list(boot_type):
	result = subprocess.check_output(["zfs", "get", "-t volume", "com.qnap:sanboot",])
	dataset_list = dict()
	for line in result.splitlines()[1:]:
		item = line.split()
		ds = dataset()
		name = item[0]
		ds.boot = item[2]
		try:
			ds.parent_name = name[:name.rindex("/")]
			ds.name = name[name.rindex("/")+1:]
			if ds.boot == boot_type:
				dataset_list[ds.name] = ds
		except:
			pass
	result = subprocess.check_output(["zfs", "get", "-t snapshot", "com.qnap:sanboot",])
	for line in result.splitlines()[1:]:
		item = line.split()
		name = item[0]
		dsname= name[:name.rindex("@")]
		snapname = name[name.rindex("@")+1:]
		if snapname == 'init' and item[2] == boot_type:
			if dataset_list.has_key(dsname[dsname.rindex("/")+1:]):
				dataset_list[dsname[dsname.rindex("/")+1:]].snapshot = 1
		else:
			pass
				

	return dataset_list

def reload_ctld():
	ctld_org_conf = open("/etc/ctl.bsd.conf", "r")
	ctld_conf = open("/etc/ctl.conf", "w")
	org_conf = ctld_org_conf.read()
	for k, ds in sanboot_dataset_list("on").items():
		org_conf = org_conf + "target iqn.2014-04.com.qnap:{0}{{\n  auth-group no-authentication\n  portal-group pg0\n    lun 0 {{\npath /dev/zvol/zdisk0/{0}\n}}\n}} ".format(ds.name) + "\n"
	for k, ds in sanboot_dataset_list("clone").items():
		org_conf = org_conf + "target iqn.2014-04.com.qnap:{0}{{\n  auth-group no-authentication\n  portal-group pg0\n    lun 0 {{\npath /dev/zvol/zdisk0/{0}\n}}\n}} ".format(ds.name) + "\n"
	ctld_conf.write(org_conf)
	ctld_conf.close()
	ctld_org_conf.close()
	subprocess.check_output(["/etc/rc.d/ctld", "reload", ])


def create_zvol(volname, volsize):
	try:
		result = subprocess.check_output(["zfs", "create", "-V", volsize, "-s", "-o", "com.qnap:sanboot=on", "zdisk0/"+volname, ])
		reload_ctld()
	except:
		pass

def clone_zvol(volname, mac):
	try:
		result = subprocess.check_output(["zfs", "clone", "-o", "com.qnap:sanboot=clone", "zdisk0/"+volname+"@"+"init", "zdisk0/"+volname+"-"+mac])
	except:
		pass

def snapshot_zvol(volname):
	try:
		result = subprocess.check_output(["zfs", "snapshot", "zdisk0/"+volname+"@"+"init", ])
	except:
		pass
def delete_zvol(volname):
	try:
		result = subprocess.check_output(["zfs", "set", "com.qnap:sanboot=off",  "zdisk0/"+volname, ])
		reload_ctld()
		time.sleep(1) # XXX
		result = subprocess.check_output(["zfs", "destroy", "-R", "zdisk0/"+volname, ])
	except:
		pass

class menu:        
	def GET(self):
		reload_ctld()
		return render.menu(sanboot_dataset_list("on"))

class clone_boot:
	def GET(self, volname, mac):
		clone_zvol(volname, mac)
		time.sleep(1) # XXX
		reload_ctld()
		time.sleep(1) # XXX
		return render.clone_boot(volname+"-"+mac)
class boot:        
	def GET(self, volname, mac):
		dataset_list = sanboot_dataset_list("on")
		if dataset_list.has_key(volname) and dataset_list[volname].snapshot == 1:
			return render.boot(volname, "-"+mac)
		return render.boot(volname, "")

class create:
	def GET(self, volname, volsize):
		create_zvol(volname, volsize)
		return "#!ipxe\nchain http://192.168.10.2:8080/menu"

class delete:
	def GET(self, volname):
		delete_zvol(volname)
		return "#!ipxe\nchain http://192.168.10.2:8080/menu"
class delete_menu:
	def GET(self):
		return render.delete(sanboot_dataset_list("on"))

class snapshot:
	def GET(self, volname):
		snapshot_zvol(volname)
		return "#!ipxe\nchain http://192.168.10.2:8080/menu"
class snapshot_menu:
	def GET(self):
		return render.snapshot(sanboot_dataset_list("on"))

if __name__ == "__main__":
    app.run()
