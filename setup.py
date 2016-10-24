from setuptools import setup, find_packages

bin_dir = '/opt/cpt/bin'
base_dir = '/opt/cpt'
gus_dir = '/opt/cpt/cptops_gus_case'
km_dir = '/opt/cpt/km'

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
                 'bin/zookeeper_status.py']

base_files = ['cptops_nagios/bin/nagios_monitor.py',
              'cptops_nagios/bin/nagios_monitor_single.py',
              'cptops_idbhost/includes/common.py',
              'cptops_idbhost/includes/idbhost.py']

km_files = [
            'cptops_exec_with_creds/km/__init__.py',
            'cptops_exec_with_creds/km/katzmeow.py'
            ]

gus_files = [
             'cptops_gus_base/__init__.py',
             'cptops_gus_base/base.py',
             'cptops_gus_base/cred.py',
             'cptops_gus_base/ssl_version.py',
             'cptops_gus_base/gusparse.py'
             ]

setup(
    name='cpt-tools',
    version='1.1',
    description='Validation scripts used by CPT during patching.',
    author='Mitchell Gaddy',
    author_email='mgaddy@salesforce.com',
    url="https://git.soma.salesforce.com/CPT/cptops_validation_tools",
    packages=find_packages(),
    data_files=[(bin_dir, bin_files),
                (base_dir, base_files),
                (gus_dir, gus_files),
                (km_dir, km_files)
                ],
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
