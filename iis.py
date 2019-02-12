import xml.etree.ElementTree as ET

import winrm
import xmltodict, json

from matilda_network.constant.matilda_enum import CreateInfra
from matilda_network.db import db_handler
from  matilda_network.constant.matilda_enum import ServiceDiscovery, Status
from matilda_network.utils import util


class IisService(object):

    def __init__(self, creds):
        self.credentials = creds

    def get_iis_discovery(self, req_data):
        name = req_data.get('name')
        for ip in req_data.get('host'):
            host = ip
            username = req_data.get('hostusername')
            password = req_data.get('hostpassword')
            config_location = req_data.get('servicepath')
            service_type_id = ServiceDiscovery.IIS.value
            status_type_id = Status.INPROGRESS.value
            data = dict(service_disc_name=name,
                        service_path=config_location,
                        ip_address=host,
                        is_active=True,
                        service_disc_start_on=util.getdatetime(),
                        status_type_id=status_type_id,
                        service_type_id=service_type_id)
            db_response = db_handler.create_iis_discovery(data)
            url = CreateInfra.http.value + ip + ':' + CreateInfra.port.value + CreateInfra.ws.value
            session = winrm.Session(url, auth=(username, password),
                                    server_cert_validation='ignore')
            service_path = req_data.get('servicepath')
            xml_path = 'Get-Content ' + service_path
            r = session.run_ps(xml_path)
            output = r.std_out.decode('utf-8')
            tree = ET.ElementTree(ET.fromstring(output))
            root = tree.getroot()
            applicationPoolDefaults = root.findall('.//applicationPoolDefaults')
            applicationPools = root.findall('.//applicationPools')
            DefaultCLRversion=''
            for element in applicationPools:
                items = dict()
                #CLR_version = ''
                #ManagedPipeline_Mode = ''
                #applicationPoolDefaults = element.findall('.//applicationPoolDefaults')
                add = element.findall('.//add')
                # print("ADDD IS ASADAASS %s" % add)
                DefaultidentityType = ''
                #db2 = []
                for element in applicationPoolDefaults:

                    DefaultCLRversion = element.attrib.get('managedRuntimeVersion')
                    # print("CLR VERSION %s"%DefaultCLRversion)
                    for child in element:
                        DefaultidentityType = child.attrib.get('identityType')
                        # print("IDENTITY TYPE IS %s"%DefaultidentityType)
                # add = element.findall('.//add')
                # # print("ADDD IS ASADAASS %s"%add)
                for element in add:
                    ApplicationPool = element.attrib.get('name')
                    #CLR_version = ''
                    IdentityType = ''
                    # ManagedPipeline_Mode = ''

                    if element.attrib.get('managedRuntimeVersion') == None:
                        CLR_version = DefaultCLRversion
                        #CLR_version = "v4.0"
                        items['version'] = CLR_version


                        # print("CLR VERSION 1 %s"%CLR_version)
                    else:
                        CLR_version = element.attrib.get('managedRuntimeVersion')
                        items['version'] = CLR_version
                    # items['version']= CLR_version
                    ## here i get final CLR version
                    if CLR_version == '':
                        CLR_version = "No Managed Code"
                    #print("FINAL CLR VERSION %s" % CLR_version)
                    #items['version'] = CLR_version
                    #sample_db_call.append(CLR_version)
                    if element.attrib.get('managedPipelineMode') == None:
                        ManagedPipeline_Mode = 'Integrated'
                        items['mode'] = ManagedPipeline_Mode
                        # print("CLR VERSION 1 %s"%CLR_version)
                    else:
                        ManagedPipeline_Mode = element.attrib.get('managedPipelineMode')
                        items['mode'] = ManagedPipeline_Mode

                    Processmodel = element.findall('.//processModel')
                    if len(Processmodel)==0:
                        IdentityType = DefaultidentityType
                    for element in Processmodel:
                        if element==None:
                            IdentityType = DefaultidentityType
                        else:
                            IdentityType = element.attrib.get('identityType')
                    #print("IDENTITY TYPEEEEE %s"%IdentityType)
                    data = dict(ApplicationPool_Name=ApplicationPool,CLR_Version=CLR_version,Identity=IdentityType,Pipeline_Mode=ManagedPipeline_Mode)
                    #print("FINAL APPLICATION POOL DATA IS %s"%data)
                    disc_id = db_response.get('service_disc_id')
                    db_apppools = db_handler.create_iis_applicationpool(data, disc_id)

            sites = root.findall('.//site')
            for element in sites:
                site_Name = element.attrib.get('name')
                site_id = element.attrib.get('id')
                application = element.findall('.//application')
                bindings = element.findall('.//binding')
                virtualdirectory = element.findall('.//virtualDirectory')
                application_pool = ''
                for element in application:
                    if not element.attrib.get('applicationPool'):
                        application_pool = 'DefaultAppPool'
                    else:
                        application_pool = element.attrib.get('applicationPool')


                db_sites = ''
                #print("TILLLLL HERE ")
                for element in virtualdirectory:
                    site_Path = element.attrib.get('physicalPath')
                    data = dict(Site_Name=site_Name, Site_Id=site_id, SiteApplicationPool=application_pool,
                                SitePath=site_Path)
                    disc_id = db_response.get('service_disc_id')
                    db_sites = db_handler.create_iis_site(data, disc_id)
                    print("NEXT TILLLLL HERE")
                    #print("sdfsfdsdsds %s" % db_sites)
                    a = 'Get-Content ' + element.attrib.get('physicalPath') + '\\Web.config'
                    try:
                        r = session.run_ps(a)
                        output = r.std_out.decode('utf-8')
                        tree = ET.ElementTree(ET.fromstring(output))
                        root = tree.getroot()
                    except:
                        pass
                    connection_string = root.findall('.//connectionStrings')
                    for element in connection_string:
                        for child in element:
                            db_name = child.attrib.get('name')
                            db_connectionString = child.attrib.get('connectionString')
                            db_providerName = child.attrib.get('providerName')
                            data = dict(DbName=db_name, DbConnectionString=db_connectionString, DbProviderName= db_providerName)
                            disc_id = db_sites.get('service_iis_site_id')
                            db_handler.create_iis_datasource(data,disc_id)

                for element in bindings:
                    binding_protocol = element.attrib.get('protocol')
                    binding_Information = element.attrib.get('bindingInformation')
                    data = dict(Binding_Protocol=binding_protocol, Binding_Information=binding_Information)

                    disc_id = db_sites.get('service_iis_site_id')
                    db_handler.create_iis_binding(data,disc_id)


            status = Status.COMPLETED.value
            print("CHECK LINE ")
            db_handler.update_iis_discovery(service_disc_id=db_response.get('service_disc_id'), status=status)




