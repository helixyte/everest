from everest.representers.xml import XmlRepresenterConfiguration

class XML_MYRESOURCE(XmlRepresenterConfiguration):
    xml_schema = 'testapp:MyResource.xsd'
    xml_ns = 'http://schemata.everest.org/myresource'
    xml_tag = 'myresource'
    xml_prefix = 'my'
