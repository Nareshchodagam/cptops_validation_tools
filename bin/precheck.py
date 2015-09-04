#!/usr/bin/python

from base import *
from hostgetter import *
import getpass



def gethostlists(dclist,cidblocal=True,debug=False,groupsize=2):
    rawresults = dict()
    for dc in dclist:
        dc = dc.upper()
        reststring = '/clusters?limit=1000'
        rawresults[dc]=gen_request(reststring,cidblocal,dc,debug)
        dcs=dict()
    print rawresults.keys()
    for key,vals in rawresults.iteritems():
        #pass1 build clusters and superpods for these clusters in a hierarchy
        clusters = dict()
        for cl in vals:

            cltemp=cl['name']
        
            if (cltemp not in clusters):
                clusters[cltemp]={}
        for cl in vals:
      #pass2 get deviceroles and hostlists back and assign to the correct cluster
            reststring = '/allhosts?cluster.name=' + cl['name'] + '&fields=name,cluster.name,deviceRole'
            current = gen_request(reststring,cidblocal,key,debug)

            deviceroles = { hval['deviceRole']  : {} for hval in current }
      #assign hosts to device roles after splitting into groups per groupsize
            for rl in deviceroles:
                deviceroles[rl] = sorted([ hval['name'] for hval in current if hval['deviceRole'] == rl ])
         
      # assign device roles to cluster
            clusters[cl['name']] = deviceroles
        dcs[key] = clusters
    j = json.dumps(dcs)

    return j
    
def get_gus_logicalhosts(session,params):
        """ returns SOQL JSON from logical host object 
            takes 2 parameters
               session : sfdc session
               params : a dict containing EITHER a named list of hostnames or a list of roles
            puts to together a SOQL where clauses based on these lists
            returns sfdc api results json or prints error message    
        """
        query = 'select Super_Pod__c, Host_Name__c, Pod__c, Role_Name__c from SM_Logical_Host__c '
        query_helper = { 'hostnames' : 'Host_Name__c', 'roles' : 'Role_Name__c' }
        
        assert(params.keys()==['hostnames'] or params.keys()==['roles'])
        lookup = params.keys()[0]
        
        myquery = query + ' where ' + ' or '.join( [ query_helper[lookup] + ' = \'' + param + '\'' for param in params[lookup] ])   
        
        gObj = Gus()
        return gObj.run_query(myquery, session)
        
            
def get_gus_loginsession():
        try:
          gpass = config.get('GUS', 'guspassword')
        except ConfigParser.NoOptionError,e:
          gpass = getpass.getpass("Please enter your GUS password: ")
    
    
        username = config.get('GUS', 'username')
    # instantiate auth object and generate session dict
        authObj = Auth(username,gpass)
        
        
        session = authObj.login()
        assert(len(session['token']) > 0)
        assert(session['instance'] == 'https://gus.my.salesforce.com')
        
        return session
    


if __name__ == "__main__":
   allidb = json.loads( gethostlists(['was','chi','tyo','asg','sjl','lon']) )
   for dc in sorted(allidb):
       for cl in sorted(allidb[dc]):
           for ro in sorted(allidb[dc][cl]):
               for host in sorted(allidb[dc][cl][ro]):
                   print('\t'.join([str(dc),str(cl),str(ro),str(host)]))
                   
   
        
