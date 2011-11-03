from everest.resources.representers.xml import XmlRepresenterConfiguration

class XML_MYRESOURCE(XmlRepresenterConfiguration):
    xml_schema='testapp:MyResource.xsd'
    xml_ns='http://schemata.cenix-bioscience.com/myresource'
    xml_tag='myresource'
    xml_prefix='my'
