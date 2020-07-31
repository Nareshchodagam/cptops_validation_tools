#!/bin/python
from setuptools import find_packages
from setuptools import setup

root_dir = '/opt/cpt'
bin_dir = '/opt/cpt/bin'
auth_dir = '/opt/cpt/bin/auth'
km_dir = '/opt/cpt/km'
gus_dir = '/opt/cpt/GUS'
remote_dir = '/opt/cpt/remote'

root_files = ['cptops_exec_with_creds/gus_case_mngr.py',
              'cptops_exec_with_creds/cptops_logicalhost_alerts.py',
              'cptops_exec_with_creds/post_comment.py',
              'cptops_exec_with_creds/update_lh.py',
              'cptops_exec_with_creds/creds_conf.py']

remote_files = ['bin/check_local_port.py',
                'bin/check_data_restore.sh',
                'bin/check_kernel_update.sh',
                'bin/check_service.sh',
                'bin/check_maxfs_desc.py',
                'bin/ifdown-eth',
                'bin/verify_if-eth.sh',
                'bin/manage_smarts.py',
                'bin/check_proxy_endpoints.py',
                'bin/check_static_routes.py',
                'bin/fix_secanchor.sh',
                'bin/insights_argus_monitor.py',
                'bin/manage_bootdevice.py',
                'bin/manage_service.py',
                'bin/manage_sharedhub.py',
                'bin/mtavalidation.py',
                'bin/start_cmgt.sh',
                'bin/stop_cmgt.sh',
                'bin/start_cmgtapi.sh',
                'bin/stop_cmgtapi.sh',
                'bin/start_netlog.sh',
                'bin/stop_netlog.sh',
                'bin/start_netevents.sh',
                'bin/stop_netevents.sh',
                'bin/validate_appauth.sh',
                'bin/validate_auth.sh',
                'bin/validate_authrad.sh',
                'bin/validate_authval.sh',
                'bin/validate_cmgt.sh',
                'bin/validate_cmgtmon.sh',
                'bin/validate_cmgtapi.sh',
                'bin/validate_csjenkinsservice.sh',
                'bin/validate_dn.sh',
                'bin/validate_honucanary',
                'bin/validate_kfora.sh',
                'bin/validate_keyproducer.sh',
                'bin/validate_linux_patchset.py',
                'bin/validate_magisterca.sh',
                'bin/validate_magistercis.sh',
                'bin/validate_magisterdb.sh',
                'bin/validate_nsm.sh',
                'bin/validate_netlog.sh',
                'bin/validate_netevents.sh',
                'bin/validate_pkica.sh',
                'bin/validate_pkicontroller.sh',
                'bin/validate_polcore.sh',
                'bin/validate_poldata.sh',
                'bin/validate_praapp.sh',
                'bin/validate_praccn.sh',
                'bin/validate_pravmh.sh',
                'bin/validate_samsecurity.sh',
                'bin/validate_secanchor.sh',
                'bin/validate_secportal.sh',
                'bin/validate_sfwupapp.sh',
                'bin/validate_sfwupproxy.sh',
                'bin/validate_sitebridge.sh',
                'bin/validate_secds.sh',
                'bin/validate_secdws.sh',
                'bin/validate_seciamsvc.sh',
                'bin/validate_secrets.sh',
                'bin/validate_smscanary.sh',
                'bin/validate_soar.sh',
                'bin/validate_splunkfwd.sh',
                'bin/validate_splunkidx.sh',
                'bin/validate_splunkmgmt.sh',
                'bin/validate_splunksrh.sh',
                'bin/validate_srdapp.sh',
                'bin/validate_syslog.sh',
                'bin/validate_vc.sh',
                'bin/validate_db.sh',
                'bin/ssa_edns_internal_validation.py',
                'bin/validate_vnscan.sh',
                'bin/validate_vnscanam.sh',
                'bin/validate_vnscanmgr.sh',
                'bin/validate_vnscanutil.sh',
                'bin/zookeeper_status.py',
                'bin/smszk_validation.sh',
                'bin/check_ircd.py',
                'bin/manage_apps.py',
                'bin/melt-fix.sh',
                'bin/restore_storage_config.sh',
                'bin/save_storage_config.sh',
                'bin/insights_disklabel.sh',
                'bin/ib-passwd-rotation.sh',
                'bin/umountall.sh',
                'bin/check_mount_generic.py',
                'bin/warden.sh',
                'bin/flowsnake_drain.py',
                'bin/dbaas_broker.sh',
                'bin/validate_smscanary.py',
                'bin/validate_smsapi.sh',
                'bin/validate_smscps.sh',
                'bin/validate_smsproxy.sh',
                'bin/validate_smsreplicator.sh',
                'bin/validate_smszk.sh',
                'bin/validate_sdb.sh',
                'bin/sam_slb_drain_service.sh',
                'includes/valid_versions.json',
                'cptops_nagios/bin/nagios_backup.sh',
                'decomm/manage_ib.py',
                'decomm/manage_ilom.py',
                'decomm/pexpect.py',
                'decomm/host_shutdown.py',
                'decomm/serial_check.py',
                'bin/write_cptrelease.py',
                'bin/cmgtapi_pingcheck.sh',
                'ssa/edns_role_internal_validation.py',
                'ssa/ddiagg_role_internal_validation.py',
                'ssa/inst_role_internal_validation.py',
                'ssa/netbot_validation.py',
                'sysfiles/files/usr/local/libexec/chk_symlinks.py',
                'sysfiles/files/usr/local/libexec/rpmdb_check.sh',
                'sysfiles/files/usr/local/libexec/system_update.sh',
                'sysfiles/files/usr/local/libexec/system_vendortools_update.sh',
                'sysfiles/files/usr/local/libexec/validate_firmware.py',
                'coresystem/files/usr/local/libexec/orb-check.py',
                'coresystem/files/usr/local/libexec/orb-lib.sh',
                'bin/validate_stride.sh',
                'bin/validate_quantumk.sh',
                'bin/validate_raphty.sh',
                'bin/validate_stampy.sh']

bin_files = ['bin/check_mq_buddy.py',
             'bin/check_reconnect.py',
             'bin/update_patching_status.py',
             'bin/check_search_buddy.py',
             'bin/synnerUtil.py',
             'bin/verify_hosts.py',
             'bin/verify_ffx_buddy.py',
             'bin/verify_search_buddy.py',
             'bin/verify_check.py',
             'bin/check_prod.py',
             'bin/checks.json',
             'bin/get_versions.py',
             'bin/get_ib_passwd.py',
             'bin/check_http_code.py',
             'bin/synthetic_check.py',
             'bin/create_batch.py',
             'bin/migration_manager.py',
             'bin/rack_port_check.py',
             'bin/scrtkafka',
             'cptops_idbhost/idbhost.py',
             'cptops_nagios/bin/nagios_monitor.py',
             'cptops_nagios/bin/nagios_monitor_single.py',
             'cptops_nagios/bin/nagios_backup.sh',
             'cptops_nagios/bin/manage_monitor.py',
             'cptops_nagios/bin/nagiosmultiprocessing.py',
             'decomm/decomm_idb.py',
             'decomm/get_RR_logs.py',
             'bin/check_master.py',
             'ssa/inst_role_external_validation.py',
             'ssa/ns_role_external_validation.py',
             'core/bin/screen_auto.sh']

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
