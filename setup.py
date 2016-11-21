from setuptools import setup, find_packages

bin_dir = '/opt/cpt/bin'

bin_files = ['bin/check_hosts.py',
                 'bin/check_local_port.py',
                 'bin/check_maxfs_desc.py',
                 'bin/check_mq_buddy.py',
                 'bin/check_proxy_endpoints.py',
                 'bin/check_reconnect.py',
                 'bin/check_search_buddy.py',
                 'bin/check_static_routes.py',
                 'bin/chk_symlinks.py',
                 'bin/manage_bootdevice.py',
                 'bin/manage_service.py',
                 'bin/mtavalidation.sh',
                 'bin/validate_linux_patchset.py',
                 'bin/verify_ffx_buddy.py',
                 'bin/verify_search_buddy.py',
                 'bin/zookeeper_status.py'
                 'cptops_sysfiles/bin/system_update.sh',
                 'cptops_sysfiles/bin/system_vendortools_update.sh',
                 'cptops_nagios/bin/nagios_monitor.py',
                 'cptops_nagios/bin/nagios_monitor_single.py',
                 'cptops_idbhost/idbhost.py']
setup(
    name='cpt-tools',
    version='1.1',
    description='Validation scripts used by CPT during patching.',
    author='Mitchell Gaddy',
    author_email='mgaddy@salesforce.com',
    url="https://git.soma.salesforce.com/CPT/cptops_validation_tools",
    packages=find_packages(),
    data_files=[(bin_dir, bin_files)],
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
