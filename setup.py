from setuptools import setup, find_packages

root_dir = '/opt/cpt'
bin_dir = '/opt/cpt/bin'
auth_dir = '/opt/cpt/bin/auth'
km_dir = '/opt/cpt/km'
gus_dir = '/opt/cpt/GUS'
remote_dir = '/opt/cpt/remote'

root_files = [ 'cptops_exec_with_creds/close_gus_cases.py',
               'cptops_exec_with_creds/cptops_logicalhost_alerts.py']

remote_files = [ 'bin/check_local_port.py',
                 'bin/check_maxfs_desc.py',
                 'bin/check_proxy_endpoints.py',
                 'bin/check_static_routes.py',
                 'bin/chk_symlinks.py',
                 'bin/manage_bootdevice.py',
                 'bin/manage_service.py',
                 'bin/mtavalidation.py',
                 'bin/validate_linux_patchset.py',
                 'bin/validate_firmware.py',
                 'bin/zookeeper_status.py',
                 'bin/check_ircd.py',
                 'bin/manage_apps.py',
                 'bin/migrate-to-centos.sh',
                 'bin/rpmdb_check.sh',
                 'includes/valid_versions.json',
                 'cptops_sysfiles/bin/system_update.sh',
                 'cptops_sysfiles/bin/system_vendortools_update.sh',
                 'cptops_nagios/bin/nagios_backup.sh' ]

bin_files = ['bin/check_mq_buddy.py',
             'bin/check_reconnect.py',
             'bin/check_search_buddy.py',
             'bin/verify_hosts.py',
             'bin/verify_ffx_buddy.py',
             'bin/verify_search_buddy.py',
             'bin/verify_check.py',
             'bin/check_prod.py',
             'bin/checks.json',
             'bin/check_http_code.py',
             'bin/synthetic_check.py',
             'cptops_idbhost/idbhost.py',
             'cptops_nagios/bin/nagios_monitor.py',
             'cptops_nagios/bin/nagios_monitor_single.py',
             'cptops_nagios/bin/nagios_backup.sh' ]

auth_files = ['cptops_idbhost/auth/internal_ca.pem']

km_files = ['cptops_exec_with_creds/km/__init__.py',
            'cptops_exec_with_creds/km/katzmeow.py']

gus_files = ['cptops_gus_base/GUS/__init__.py',
             'cptops_gus_base/GUS/auth.py',
             'cptops_gus_base/GUS/base.py',
             'cptops_gus_base/GUS/cred.py',
             'cptops_gus_base/GUS/gusparse.py',
             'cptops_gus_base/GUS/ssl_version.py']

setup(
    name='cpt-tools',
    version='2.0',
    description='Validation scripts used by CPT during patching.',
    author='Mitchell Gaddy',
    author_email='mgaddy@salesforce.com',
    url="https://git.soma.salesforce.com/CPT/cptops_validation_tools",
    packages=find_packages(),
    data_files=[(bin_dir, bin_files),
                (auth_dir, auth_files),
                (km_dir, km_files),
                (remote_dir, remote_files),
                (gus_dir, gus_files),
                (root_dir, root_files)],
    classifiers=[
          "License :: Salesforce Proprietary Code",
          "Programming Language :: Python",
          "Development Status :: 1 - Alpha",
          "Intended Audience :: Developers",
          "Topic :: Build",
    ],
    keywords='cpt tools',
    license='Salesforce Proprietary Code',
    )
